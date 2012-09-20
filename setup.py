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
      install_requires='Trac >=0.13dev',
      description='Mercurial plugin for Trac multirepos branch',
      keywords='trac scm plugin mercurial hg',
      version='0.13.0.0',
      url=MyPagePlugin,
      license='GPL',
      author='Christian Boos',
      author_email='cboos@edgewall.org',
      long_description="""
      This plugin for Trac 0.13 provides support for maintaining 
      a personal journal in the form of wiki pages.

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
