# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.thumb
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
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

from distutils.core import setup, Extension
import os
import sys

# list og source files
files = ["src/thumbnail.c", "src/png.c" ]

include_dirs = []
library_dirs = []
libraries    = [ 'png' ]

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


config_h = open('src/config.h', 'w')
if check_config('epeg', '0.9'):
    print 'epeg extention enabled'
    config_h.write('#define USE_EPEG\n')
else:
    print 'epeg extention disabled'
config_h.close()


# the thumbnail extention module
ext_modules = [ Extension("kaa.thumb._thumbnailer", files,
                          library_dirs=library_dirs,
                          include_dirs=include_dirs,
                          libraries=libraries) ]

# create fake kaa.__init__.py
open('__init__.py', 'w').close()

# call setup
setup(name="kaa-thumb", version="0.1",
      ext_modules = ext_modules,
      package_dir = {"kaa": ".",
                     "kaa.thumb": "src" },
      packages = [ 'kaa.thumb' ],
      py_modules=[ 'kaa.__init__' ],
      scripts     = [ 'bin/kaa-thumb' ],
      )

# delete fake kaa.__init__.py
os.unlink('__init__.py')

# delete src/config.h
os.unlink('src/config.h')
