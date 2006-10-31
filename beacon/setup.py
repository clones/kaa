# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.beacon
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2005 Jason Tackaberry, Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
#                Jason Tackaberry <tack@sault.org>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

# python imports
import sys

try:
    # kaa base imports
    from kaa.distribution import Extension, setup
except ImportError:
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

ext_modules = [ thumb_ext ]


setup (module      = 'beacon',
       version     = '0.1',
       description = "Media-oriented virtual filesystem",
       scripts     = [ 'bin/kaa-thumb', 'bin/beacon' ],
       ext_modules = ext_modules
      )
