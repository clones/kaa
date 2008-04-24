# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.display
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.display - Display module
# Copyright (C) 2005, 2006 Dirk Meyer, Jason Tackaberry
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
import popen2

try:
    # kaa base imports
    from kaa.distribution.core import *
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# config file
config = ConfigFile('src/config.h')

check_library('X11', ['<X11/Xlib.h>'], '')
check_library('imlib2', '1.1.1')
evas = check_library('evas', '0.9.9.010')
check_library('directfb', '0.9.20')

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

except ImportError, e:
    print 'not installed'
    pygame = False


# extention modules
modules = []

if get_library('imlib2'):
    config.define('USE_IMLIB2')
if get_library('evas'):
    config.define('USE_EVAS')

if get_library('X11'):

    # the display so module
    x11 = Extension('kaa.display._X11module',
                    [ 'src/x11.c', 'src/x11display.c', 'src/x11window.c',
                      'src/common.c' ],
                    libraries = ['png', 'rt'])

    config.define('HAVE_X11')

    if check_library('XComposite', ['<X11/extensions/Xcomposite.h>'], libraries = ['Xcomposite']):
        config.define('HAVE_X11_COMPOSITE')
        x11.add_library('XComposite')
        
    features = { 'with': [], 'without': [] }
    imlib2 = get_library('imlib2')
    if imlib2 and imlib2.compile(['<Imlib2.h>'], 'imlib_context_set_display(NULL);'):
        config.define('USE_IMLIB2_X11')
        x11.add_library('imlib2')
        features['with'].append('imlib2')
    else:
        features['without'].append('imlib2')

    if evas and evas.compile(['<Evas.h>', '<Evas_Engine_Software_X11.h>']):
        features['with'].append('evas')
        x11.add_library('evas')
        config.define('ENABLE_ENGINE_SOFTWARE_X11')
    else:
        features['without'].append('evas')

    if evas and evas.compile(['<Evas.h>', '<Evas_Engine_GL_X11.h>']):
        features['with'].append('evasGL')
        x11.add_library('evas')
        x11.libraries.append("GL")
        config.define('ENABLE_ENGINE_GL_X11')
    else:
        features['without'].append('evasGL')

    features = ', '.join(features['with'] + [ 'no %s' % x for x in features['without'] ])
    print '+ X11 (%s)' % features
    modules.append(x11)
else:
    print '- X11'


if get_library('imlib2'):

    # the framebuffer so module
    fb = Extension('kaa.display._FBmodule', 
                   [ 'src/fb.c', 'src/common.c'])
    fb.add_library('imlib2')
    if evas and evas.compile(['<Evas.h>', '<Evas_Engine_FB.h>']):
        fb.add_library('evas')
        config.define('ENABLE_ENGINE_FB')
        print "+ Framebuffer (imlib2, evas)"
    else:
        print "+ Framebuffer (imlib2, no evas)"
    modules.append(fb)
else:
    print "- Framebuffer"


if get_library('directfb'):

    # the dfb so module
    dfb = Extension('kaa.display._DFBmodule', [ 'src/dfb.c', 'src/common.c'] )
    dfb.add_library('directfb')
    if evas and evas.compile(['<Evas.h>', '<Evas_Engine_DirectFB.h>'], extra_libraries = ['directfb']):
        print "+ DirectFB (evas)"
        dfb.add_library('evas')
        config.define('ENABLE_ENGINE_DIRECTFB')
    else:
        print "+ DirectFB"
    modules.append(dfb)
else:
    print "- DirectFB"


if pygame and get_library('sdl') and get_library('imlib2'):

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
                        'imlib2 >= 1.2.1, python-kaa-evas >= 0.1.0, evas >= 0.9.9.032'
build_requires_common = 'python-kaa-base >= 0.1.2, pygame-devel >= 1.6.0, python-kaa-imlib2 >= 0.2.0,' \
                        'imlib2-devel >= 1.2.1, python-kaa-evas >= 0.1.0, evas-devel >= 0.9.9.032'

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
