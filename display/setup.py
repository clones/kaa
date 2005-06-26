# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.display
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
#
# First Edition: Jason Tackaberry <tack@sault.org>
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

from distutils.core import setup, Extension

files = [ 'src/display.c', 'src/sdl.c' ]

include_dirs = []
library_dirs = []
libraries    = ['png', "rt"]

def check_config(name, minver):
    """
    Check dependencies add add the flags to include_dirs, library_dirs and
    libraries. The basic logic is taken from pygame.
    """
    command = name + '-config --version --cflags --libs 2>/dev/null'
    try:
        config = os.popen(command).readlines()
        if len(config) == 0:
            raise ValueError, 'command not found'
        flags  = (' '.join(config[1:]) + ' ').split()
        ver = config[0].strip()
        if minver and ver < minver:
            err= 'requires %s version %s (%s found)' % \
                 (name, minver, ver)
            raise ValueError, err
        for f in flags:
            if f[:2] == '-I':
                include_dirs.append(f[2:])
            if f[:2] == '-L':
                library_dirs.append(f[2:])
            if f[:2] == '-l':
                libraries.append(f[2:])
        return True
    except Exception, e:
        print 'WARNING: "%s-config" failed: %s' % (name, e)
        return False


if not check_config('imlib2', '1.1.1'):
    print 'Imlib2 >= 1.1.1 not found'
    print 'Download from http://enlightenment.freedesktop.org/'
    sys.exit(1)

# create config file
config_h = open('src/config.h', 'w')

if 'X11' in libraries:
    # files.append('src/X11.c')
    config_h.write('#define USE_IMLIB2_DISPLAY\n')
else:
    print 'Imlib2 compiled without X11, not building X11 display'


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
    if not check_config('sdl', '1.2.5'):
        print 'SDL not found'
        raise ImportError
    include_dirs.append(inc)
    config_h.write('#define USE_PYGAME\n')
except ImportError:
    print 'pygame support disabled'

config_h.close()

# create fake kaa.__init__.py
open('src/__init__.py', 'w').close()

setup(name="kaa-display", version="0.1",
    ext_modules=[
    Extension("kaa._display",
              files,
              library_dirs=library_dirs,
              include_dirs=include_dirs,
              libraries=libraries)
    ],
    py_modules=["kaa.display"],
    package_dir = {"kaa": "src" }
)

# delete fake kaa.__init__.py
os.unlink('src/__init__.py')

# delete src/config.h
os.unlink('src/config.h')
