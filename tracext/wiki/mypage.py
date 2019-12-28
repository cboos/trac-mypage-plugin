# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2012 Christian Boos <cboos@edgewall.org>
# All rights reserved.
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.
#
# Author: Christian Boos <cboos@edgewall.org>

from bisect import bisect
from datetime import datetime
import pkg_resources

from trac.util.html import tag

from trac.config import Option
from trac.core import *
from trac.resource import ResourceNotFound
from trac.util import get_reporter_id
from trac.util.datefmt import format_date, localtz, parse_date, user_time
from trac.util.translation import cleandoc_, domain_functions
from trac.wiki.api import WikiSystem
from trac.wiki.formatter import format_to_oneliner
from trac.wiki.model import WikiPage
from trac.wiki.macros import WikiMacroBase
from trac.web.api import IRequestHandler
from trac.web.chrome import INavigationContributor

import re

_, N_, add_domain, gettext = \
    domain_functions('mypage', ('_', 'N_', 'add_domain', 'gettext'))


class MyPageModule(Component):
    """Very simple personal journal-in-a-wiki tool.

    For now, only authenticated users can use it, and they must have
    all the appropriate wiki permissions (`WIKI_VIEW` and `WIKI_CREATE`).

    The `PageTemplates/MyPage` wiki page or the more specific
    `PageTemplates/MyPage/<user>` page will be used to prefill
    the content of the //page of the day// when creating it
    using the ''MyPage'' main navigation entry.

    Such template pages can even contain special tokens that will get
    substituted with some content.  Use the [[MyPageHelp]] macro to
    learn about those tokens.
    """

    implements(INavigationContributor, IRequestHandler)

    prefix = Option('mypage', 'prefix', '', doc="""
        Prefix to use for grouping ''MyPage'' pages. Those pages which
        will have a name of the form
        `<prefix>/<user>/<date>`.

        The prefix defaults to empty, which means the MyPage pages
        will simply be rooted at toplevel and have a form of
        `<user>/<date>`.
        """)

    # List of "variables" that can be placed in PageTemplates/MyPage
    # and expanded.

    tokens = {
        'date': (
            '$MYPAGE_DATE',
            N_("The date of the day, formatted according "
               "to the user preferences")),
        'isodate': (
            '$MYPAGE_ISODATE',
            N_("The date of the day, formatted according ISO-8601 "
               "(i.e. YYYY-MM-DD)")),
        'user': (
            '$MYPAGE_USER',
            N_("The author's user id")),
        'author': (
            '$MYPAGE_AUTHOR',
            N_("The author's full name")),
        'lp_link': (
            '$MYPAGE_LAST_PAGE_LINK',
            N_("Link to most recent `MyPage` page")),
        'lp_name': (
            '$MYPAGE_LAST_PAGE_NAME',
            N_("Name of the most recent `MyPage` page")),
        'lp_text': (
            '$MYPAGE_LAST_PAGE_TEXT',
            N_("Wiki text of the most recent `MyPage` page")),
        'lp_quoted': (
            '$MYPAGE_LAST_PAGE_QUOTED',
            N_("Wiki-quoted text of the most recent `MyPage` page")),
        }

    def __init__(self):
        locale_dir = pkg_resources.resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)

    # Public methods

    def get_mypage_base(self, authname):
        """Determine base name for given user.
        """
        return ''.join(c + '/' for c in [self.prefix, authname] if c)

    def get_all_mypages(self, base):
        """Return the list of MyPage pages for the given `base`

        (where `base` is usually as given by `get_mypage_base`)
        """
        compiled = re.compile(".*/\d{4}-\d{2}-\d{2}")
        pages = list(WikiSystem(self.env).get_pages(base))
        datepages = [date for date in pages if not compiled.match(date) is None]
        return sorted(datepages)

    # INavigationContributor

    def get_active_navigation_item(self, req):
        """Check whether the current request belongs to MyPage.

        Note: actually this won't work... the wiki module will always
              take over (see `prepare_request` in trac/web/chrome.py).
        """
        return req.authname and \
            req.path_info.startswith('/wiki/' +
                                     self.get_mypage_base(req.authname))

    def get_navigation_items(self, req):
        """Retrieve top-level ''MyPage'' entry.
        """
        yield 'mainnav', 'mypage', tag.a(_("MyPage"), href=req.href.mypage())


    # IRequestHandler methods

    def match_request(self, req):
        """Return whether the handler wants to process the given request.
        """
        if req.path_info.rstrip('/') == '/mypage':
            if not req.authname:
                raise PermissionError(_("""
                    You need to be authenticated in order to use MyPage.
                    """))
            return True

    def process_request(self, req):
        """Process the request
        """
        base = self.get_mypage_base(req.authname)
        tzinfo = getattr(req, 'tz', None)
        now = datetime.now(tzinfo or localtz)
        today = format_date(now, 'iso8601', tzinfo)
        today_page_name = base + today
        today_page = WikiPage(self.env, today_page_name)
        if today_page.exists:
            req.redirect(req.href.wiki(today_page_name, action='edit'))

        # create page of the day for today
        if 'WIKI_CREATE' not in req.perm(today_page.resource):
            raise ResourceNotFound(_("Can't create the page of the day."))
        ws = WikiSystem(self.env)
        def get_page_text(pagename):
            if ws.has_page(pagename):
                page = WikiPage(self.env, pagename)
                if 'WIKI_VIEW' in req.perm(page.resource):
                    self.log.debug("get_page_text(%s) -> %s",
                                   pagename, page.text)
                    return page.text
            self.log.debug("get_page_text(%s) -> None", pagename)

        # retrieve page template
        template_name = 'PageTemplates/MyPage'
        mytemplate_name = '/'.join([template_name, req.authname])
        template_text = get_page_text(mytemplate_name)
        if template_text is None:
            template_text = get_page_text(template_name)

        text = last_page_text = last_page_quoted = None
        if template_text is not None:
            # retrieve previous "page of the day", if any
            all_mypages = self.get_all_mypages(base)
            last = bisect(all_mypages, today_page_name) - 1
            self.log.debug("Pos of today %s in %r is %d",
                           today_page_name, all_mypages, last)
            last_page_name = all_mypages[last] if last >= 0 else None
            last_page_link = ''
            if last_page_name:
                last_page_link = '[[%s]]' % last_page_name
                last_page_text = get_page_text(last_page_name)
                if last_page_text is not None:
                    last_page_quoted = '\n'.join(
                        ['> ' + line for line in last_page_text.splitlines()])

            today_user = user_time(req, format_date, now, tzinfo=tzinfo)
            author = get_reporter_id(req)

            text = template_text \
                .replace(self.tokens['date'][0], today_user) \
                .replace(self.tokens['isodate'][0], today) \
                .replace(self.tokens['user'][0], req.authname) \
                .replace(self.tokens['author'][0], author) \
                .replace(self.tokens['lp_link'][0], last_page_link) \
                .replace(self.tokens['lp_name'][0], last_page_name or '') \
                .replace(self.tokens['lp_text'][0], last_page_text or '') \
                .replace(self.tokens['lp_quoted'][0], last_page_quoted or '')
        req.redirect(req.href.wiki(today_page_name, action='edit', text=text))
        # Hm, wish this could force a POST...


class MyPageHelpMacro(WikiMacroBase):
    _domain = 'mypage'
    _description = cleandoc_("Display help for `PageTemplates/MyPage/` usage.")

    def expand_macro(self, formatter, name, content):
        def wikify(text):
            return format_to_oneliner(self.env, formatter.context, text)

        return tag.div(
            tag.p(wikify(_("""
                The following tokens can be used in the `PageTemplates/MyPage`
                or `PageTemplates/MyPage/<user>` wiki pages:
                """))),
            tag.dl([(tag.dt(tag.tt(token)),
                     tag.dd(wikify(gettext(description))))
                    for token, description in
                    sorted(MyPageModule(self.env).tokens.values())]),
            tag.p(wikify(_("""
                Note that you can also use the `[[MyPageNav]]` wiki macro for
                creating dynamic links to other ''MyPage'' pages (use
                `[[MyPageNav?]]` to get help on this macro).
                """)))
            )


class MyPageNavMacro(WikiMacroBase):
    _domain = 'mypage'
    _description = cleandoc_("""
        Link to another `MyPage` page, with the current one taken as
        reference.

        It can take parameters of the form //`[+-offset,]label`//.

        The `offset` is +0 by default, which means link to the current
        page. A value of `+1` means the ''MyPage'' coming immediately
        after the one containing the macro. Likewise, `-1` means the
        one immediately before.

        If the macro is placed on a page which is not a ''MyPage''
        page itself, then this will take the page of the day for the
        reference point.

        Note that bigger numbers can be used for the offsets,
        so one can create links like:
        `[[MyPageNav(-100000,At the beginning)]]` and
        `[[MyPageNav(+100000,At the end)]]`.
        """)

    def expand_macro(self, formatter, name, content):
        offset = +1
        label = None
        if content is not None:
            if ',' in content:
                offset, label = content.split(',', 1)
            elif content and content[0] in '+-':
                offset = content
            else:
                label = content
            try:
                offset = int(offset)
            except ValueError:
                offset = 0
        mp = MyPageModule(self.env)
        base = mp.get_mypage_base(formatter.perm.username)
        all_mypages = mp.get_all_mypages(base)
        tzinfo = getattr(formatter.context.req, 'tz', None)
        r = formatter.resource
        if r.realm == 'wiki' and r.id.startswith(base):
            mypage = r.id
        else:
            now = datetime.now(tzinfo or localtz)
            today = format_date(now, 'iso8601', tzinfo)
            mypage = '/'.join([base, today])
        selected = base
        idx = bisect(all_mypages, mypage)

        # adjust to actual position if mypage exists
        if 0 <= idx - 1 < len(all_mypages) and all_mypages[idx -1] == mypage:
            idx -= 1
        self.log.debug("Reference is %s, pos %d in %r",
                       mypage, idx, all_mypages)

        # Special cases: at the beginning or at the end, the
        # predecessors resp. successors are "missing"
        missing = False
        if idx >= len(all_mypages) - 1 and offset > 0:
            missing, tooltip = True, _("(at the end)")
        elif idx < 1 and offset < 0:
            missing, tooltip = True, _("(at the beginning)")
        if missing:
            if not label:
                label, tooltip = tooltip, None
            return tag.a(label, title=tooltip, class_='missing')

        # Link to the targeted `MyPage` page
        idx += offset
        selected = all_mypages[max(0, min(idx, len(all_mypages) - 1))]
        self.log.debug("With offset %d, going to %d (adjusted to %d)",
                       offset, idx, max(0, min(idx, len(all_mypages) - 1)))
        selected_day = selected.split('/')[-1]
        try:
            tooltip = _("MyPage for %(day)s",
                        day=format_date(parse_date(selected_day), 'iso8601', tzinfo))
        except TracError:
            tooltip = _("non-day page '%(special)s'", special=selected_day)
        return tag.a(label if label is not None else selected, title=tooltip,
                     href=formatter.href.wiki(selected))
