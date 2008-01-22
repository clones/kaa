# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.beacon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
#                Jason Tackaberry <tack@sault.org>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

# python imports
import sys

# We require python 2.5 or later, so complain if that isn't satisfied.
if sys.version.split()[0] < '2.5':
    print "Python 2.5 or later required."
    sys.exit(1)

try:
    # kaa base imports
    from kaa.distribution.core import Extension, setup
except ImportError, e:
    print e
    print 'kaa.base not installed'
    sys.exit(1)

thumb_ext = Extension("kaa.beacon._libthumb",
                      ["src/libthumb.c", "src/libpng.c" ],
                      config='src/config.h')

if not thumb_ext.check_library('imlib2', '1.1.1'):
    print 'Imlib2 >= 1.1.1 not found'
    print 'Download from http://enlightenment.freedesktop.org/'
    sys.exit(1)

if not thumb_ext.check_library('libpng', '1.2.0'):
    print 'libpng >= 1.2.0 not found'
    sys.exit(1)

if thumb_ext.check_library('epeg', '0.9'):
    print 'epeg extention enabled'
    thumb_ext.config('#define USE_EPEG')
else:
    print 'epeg extention disabled'

try:
    from pysqlite2 import dbapi2 as sqlite
    if sqlite.version_info < ( 2, 3 ):
        version = '.'.join([ str(x) for x in sqlite.version_info ])
        print 'pysqlite2 >= 2.3.0 required, found %s' % version
        sys.exit(1)
except ImportError:
    print 'pysqlite2 is not installed'
    sys.exit(1)
    
ext_modules = [ thumb_ext ]


setup (module      = 'beacon',
       version     = '0.1.0',
       license     = 'LGPL',
       summary     = "Media-oriented virtual filesystem",
       scripts     = [ 'bin/kaa-thumb', 'bin/beacon-daemon', 'bin/beacon-search',
                       'bin/beacon-mount' ],
       rpminfo     = {
           'requires':       'python-kaa-base >= 0.1.2, imlib2 >= 1.2.1',
           'build_requires': 'python-kaa-base >= 0.1.2, imlib2-devel >= 1.2.1, python-devel >= 2.4.0'
       },
       ext_modules = ext_modules
      )
