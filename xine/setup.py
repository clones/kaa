# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.xine
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
#
# Maintainer:    Jason Tackaberry <tack@sault.org>
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
import sys, os

try:
    # kaa base imports
    from kaa.distribution import Extension, Configfile, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# config file
config = Configfile('src/config.h')

# check for X11
x11 = Extension('kaa.display._Displaymodule',
                [ 'src/display.c', 'src/sdl.c', 'src/x11display.c',
                  'src/x11window.c', 'src/imlib2.c', 'src/evas.c' ],
                libraries = ['png', 'rt'])

# check if X11 is actually present
if not x11.check_cc(['<X11/Xlib.h>'], '', '-lX11'):
    print "System without X11 detected! Disabling all X11 dependencies..."
    x11 = None
else:
    config.define('HAVE_X11')

files = ['src/xine.c', 'src/video_port.c', 'src/audio_port.c', 'src/stream.c',
         'src/post.c', 'src/drivers/video_out_kaa.c',
         'src/post_out.c', 'src/post_in.c', 'src/event.c', 'src/event_queue.c',
         'src/utils.c', 'src/vo_driver.c', 'src/drivers/kaa.c',
         'src/drivers/yuv2rgb.c', 'src/drivers/yuv2rgb_mmx.c', 'src/drivers/dummy.c',
         'src/drivers/video_out_dummy.c', 'src/drivers/common.c', 'src/drivers/fb.c'
        ]

if x11:
    files.append('src/drivers/x11.c')
    xineso = Extension('kaa.xine._xinemodule', files,
                       libraries = ["X11"], 
                       # FIXME: don't hardcode this path
                       library_dirs = ["/usr/X11R6/lib"])
else:
    xineso = Extension('kaa.xine._xinemodule', files)
    
if not xineso.check_library('xine', '1.1.1'):
    print 'xine >= 1.1.1 not found'
    print 'Download from http://xinehq.de'
    config.unlink()
    sys.exit(1)

arch = os.popen("uname -i").read().strip()
if arch == "x86_64":
    config.define('ARCH_X86_64')
elif arch == "i386":
    config.define('ARCH_X86')

setup(module      = 'xine',
      version     = '0.9', # We're almost feature complete :)
      ext_modules = [ xineso ]
)

config.unlink()
