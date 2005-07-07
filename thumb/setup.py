# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.thumb
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Thumbnail module for python
# Copyright (C) 2005 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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
    from kaa.base.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)
    
thumbnailer = Extension("kaa.thumb._thumbnailer",
                        ["src/thumbnail.c", "src/png.c" ],
                        libraries = ['png'], config='src/config.h')

if not thumbnailer.check_library('imlib2', '1.1.1'):
    print 'Imlib2 >= 1.1.1 not found'
    print 'Download from http://enlightenment.freedesktop.org/'
    sys.exit(1)

if not thumbnailer.check_cc([], '', '-lpng'):
    print 'Error: libpng is missing.'
    sys.exit(1)

if not thumbnailer.check_cc(['<png.h>'], '', '-lpng'):
    print 'Error: libpng header file is missing.'
    sys.exit(1)

if thumbnailer.check_library('epeg', '0.9'):
    print 'epeg extention enabled'
    thumbnailer.config('#define USE_EPEG')
else:
    print 'epeg extention disabled'

# call setup
setup(module      = 'thumb',
      version     = '0.1',
      ext_modules = [ thumbnailer ],
      scripts     = [ 'bin/kaa-thumb' ],
      )
