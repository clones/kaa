# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.Imlib2
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

# python imports
import sys

try:
    # kaa base imports
    from kaa.base.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)
    
files = [ 'src/imlib2.c', 'src/image.c', 'src/font.c', 'src/rawformats.c' ]
imlib2so = Extension('kaa.imlib2._Imlib2module', files,
                     libraries = ['png', 'rt'],
                     config='src/config.h')

def check_link(code, args):
    outfile = "/tmp/a.out.%d" % os.getpid()
    f = os.popen("cc -x c - -o %s %s &>/dev/null" % (outfile, args), "w")
    if not f:
        return False

    f.write(code)
    result = f.close()

    if os.path.exists(outfile):
        os.unlink(outfile)

    return result == None


if not imlib2so.check_library('imlib2', '1.1.1'):
    print 'Imlib2 >= 1.1.1 not found'
    print 'Download from http://enlightenment.freedesktop.org/'
    sys.exit(1)


if 'X11' in imlib2so.libraries:
    files.append('src/display.c')
    imlib2so.config('#define USE_IMLIB2_DISPLAY')
else:
    print 'Imlib2 compiled without X11, not building kaa-imlib2 display'

if imlib2so.check_cc(['<fcntl.h>'], 'shm_open("foobar");', '-lrt'):
    imlib2so.config('#define HAVE_POSIX_SHMEM')
    print "POSIX shared memory enabled"
else:
    print "POSIX shared memory disabled"


setup(module      = 'imlib2',
      version     = '0.1',
      ext_modules = [ imlib2so ]
)
