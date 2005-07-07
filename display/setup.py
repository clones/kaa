# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.display
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
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

import re
import os
import sys

# python imports
import sys

try:
    # kaa base imports
    from kaa.base.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)
    
display = Extension('kaa.display._Displaymodule',
                    [ 'src/display.c', 'src/sdl.c' ],
                    libraries = ['png', 'rt'],
                    config='src/config.h')


if not display.check_library('imlib2', '1.1.1'):
    print 'Imlib2 >= 1.1.1 not found'
    print 'Download from http://enlightenment.freedesktop.org/'
    sys.exit(1)

if 'X11' in display.libraries:
    display.config('#define USE_IMLIB2_DISPLAY')
else:
    print 'Imlib2 compiled without X11, not building imlib2 display'

try:
    # test for pygame support
    try:
        import pygame
    except ImportError, e:
        print 'pygame not found'
        raise e
    inc = re.sub("/(lib|lib64)/", "/include/",
                 pygame.__path__[0]).replace("site-packages/", "")
    if not os.path.isdir(inc):
        print 'Error: pygame header file not found. Install pygame-devel'
        raise ImportError
    if not display.check_library('sdl', '1.2.5'):
        print 'SDL not found'
        raise ImportError
    display.include_dirs.append(inc)
    display.config('#define USE_PYGAME\n')
except ImportError:
    print 'pygame support disabled'



setup(module  = 'display',
      version = '0.1',
      ext_modules= [ display ]
)
