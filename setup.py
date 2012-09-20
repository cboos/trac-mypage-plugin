#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2005-2012 Edgewall Software
# Copyright (C) 2005-2012 Christian Boos <cboos@edgewall.org>
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

from setuptools import setup

extra = {}

try:
    import babel

    extra['message_extractors'] = {
        'tracext': [
            ('**.py', 'python', None),
        ],
    }

    from trac.util.dist import get_l10n_cmdclass
    extra['cmdclass'] = get_l10n_cmdclass()

except ImportError:
    pass

MyPagePlugin = 'http://trac-hacks.org/wiki/MyPagePlugin'

setup(name='MyPage',
      install_requires='Trac >=1.0dev',
      description='Trac plugin for editing personal journal wiki pages',
      keywords='trac wiki plugin',
      version='1.0.0.1',
      url=MyPagePlugin,
      license='GPL',
      author='Christian Boos',
      author_email='cboos@edgewall.org',
      long_description="""
      This plugin for Trac 1.0 provides support for quickly accessing
      and editing a personal journal or TODO list in the form of wiki
      pages.

      See %s for more details.
      """ % MyPagePlugin,
      namespace_packages=['tracext'],
      packages=['tracext', 'tracext.wiki'],
      package_data={
          '': ['COPYING', 'README'],
          'tracext.hg': ['locale/*.*', 'locale/*/LC_MESSAGES/*.*'],
          },
      entry_points={'trac.plugins': 'mypage = tracext.wiki.mypage'},
      **extra)
