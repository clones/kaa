# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.display
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.display - Display module
# Copyright (C) 2005, 2006, 2008 Dirk Meyer, Jason Tackaberry
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
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
import re
import os
import sys

try:
    # kaa base imports
    from kaa.distribution.core import *
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# check disable parameter
disable = []
for arg in sys.argv[:]:
    if arg.startswith('--disable-'):
        disable.append(arg[10:])
        sys.argv.remove(arg)

# config file
config = ConfigFile('src/config.h')

check_library('X11', ['<X11/Xlib.h>'], '')
check_library('imlib2', '1.1.1')

print 'checking for pygame', '...',
sys.__stdout__.flush()

try:
    import pygame
    print 'ok'
    print 'checking for pygame header files', '...',
    inc = re.sub("/(lib|lib64)/", "/include/",
                 pygame.__path__[0]).replace("site-packages/", "")
    if not os.path.isdir(inc):
        raise ImportError
    print 'ok'
    check_library('sdl', '1.2.5')
    pygame = inc
except ImportError:
    print 'not installed'
    pygame = False

# extention modules
modules = []

if get_library('imlib2'):
    config.define('USE_IMLIB2')

if get_library('X11'):

    # the display so module
    x11 = Extension('kaa.display._X11module',
                    [ 'src/x11.c', 'src/x11display.c', 'src/x11window.c',
                      'src/common.c' ],
                    libraries = ['rt'])

    config.define('HAVE_X11')

    if check_library('XComposite', ['<X11/extensions/Xcomposite.h>'], libraries = ['Xcomposite']):
        config.define('HAVE_X11_COMPOSITE')
        x11.add_library('XComposite')

    imlib2 = get_library('imlib2')
    if 'imlib2-x11' in disable or 'imlib2' in disable:
        print '+ X11 (no imlib2)'
    elif imlib2 and imlib2.compile(['<Imlib2.h>'], 'imlib_context_set_display(NULL);'):
        config.define('USE_IMLIB2_X11')
        x11.add_library('imlib2')
        print '+ X11 (imlib2)'
    elif imlib2:
        print
        print 'Imlib2 was compiled without X11 support. Therefore Imlib2 for the'
        print 'kaa.display.X11 module is disabled. Please re-compile imlib2 with X11'
        print 'support or add --disable-imlib2-x11 to the setup.py parameter'
        print
        sys.exit(1)
    else:
        print
        print 'Imlib2 not found. Therefore Imlib2 for the kaa.display.X11 module is'
        print 'disabled. Please install imlib2 or add --disable-imlib2 to the setup.py'
        print 'parameter.'
        print
        sys.exit(1)
    modules.append(x11)
else:
    print '- X11'


if get_library('imlib2') and not 'imlib2' in disable:
    # the framebuffer so module
    fb = Extension('kaa.display._FBmodule', [ 'src/fb.c', 'src/common.c'])
    fb.add_library('imlib2')
    print "+ Framebuffer (imlib2)"
    modules.append(fb)
else:
    print "- Framebuffer"


if pygame and get_library('sdl') and get_library('imlib2') and not 'imlib2' in disable:

    # pygame module
    sdl = Extension('kaa.display._SDLmodule', ['src/sdl.c', 'src/common.c'])
    sdl.add_library('imlib2')
    sdl.add_library('sdl')
    sdl.include_dirs.append(pygame)
    modules.append(sdl)
    print "+ SDL (imlib2)"
else:
    print "- SDL"


requires_common       = 'python-kaa-base >= 0.1.2, pygame >= 1.6.0, python-kaa-imlib2 >= 0.2.0,' \
                        'imlib2 >= 1.2.1'
build_requires_common = 'python-kaa-base >= 0.1.2, pygame-devel >= 1.6.0, python-kaa-imlib2 >= 0.2.0,' \
                        'imlib2-devel >= 1.2.1'

setup(module  = 'display',
      version     = '0.1.0',
      license     = 'LGPL',
      summary     = 'Python API providing Low level support for various displays, such as X11 or framebuffer.',
      rpminfo     = {
          'requires':       'libX11 >= 1.0.0, ' + requires_common,
          'build_requires': 'libX11-devel >= 1.0.0, ' + build_requires_common,
          'fc4': {
              'requires':       'xorg-x11 >= 6.8.0, ' + requires_common,
              'build_requires': 'xorg-x11-devel >= 6.8.0, ' + build_requires_common
          }
      },
      ext_modules = modules
)

config.unlink()
