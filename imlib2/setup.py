# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.Imlib2
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.imlib2 - An imlib2 wrapper for Python
# Copyright (C) 2004-2006 Jason Tackaberry <tack@sault.org>
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
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
import os
import sys

try:
    # kaa base imports
    from kaa.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

files = [ 'src/imlib2.c', 'src/image.c', 'src/font.c', 'src/rawformats.c' ]
libraries = [ 'png']
if not os.uname()[0] in ('FreeBSD', 'Darwin'):
    libraries.append('rt')
imlib2so = Extension('kaa.imlib2._Imlib2module', files,
                     libraries = libraries, config='src/config.h')


if not imlib2so.check_library('imlib2', '1.2.1'):
    print 'Imlib2 >= 1.2.1 not found'
    print 'Download from http://enlightenment.freedesktop.org/'
    sys.exit(1)


if imlib2so.check_cc(['<fcntl.h>'], 'shm_open("foobar");', '-lrt'):
    imlib2so.config('#define HAVE_POSIX_SHMEM')
    print "POSIX shared memory enabled"
else:
    print "POSIX shared memory disabled"


setup(module      = 'imlib2',
      version     = '0.2.1',
      license     = 'LGPL',
      summary     = 'Python bindings for Imlib2',
      rpminfo     = {
          'requires':       'python-kaa-base >= 0.1.2, imlib2 >= 1.2.1',
          'build_requires': 'python-kaa-base >= 0.1.2, imlib2-devel >= 1.2.1'
      },
      ext_modules = [ imlib2so ]
)
