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
import sys

try:
    # kaa base imports
    from kaa.base.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)
    
files = ['src/xine.c', 'src/video_port.c', 'src/audio_port.c', 'src/stream.c',
         'src/post.c', 'src/drivers/x11.c', 'src/drivers/buffer.c',
         'src/post_out.c', 'src/post_in.c', 'src/event.c', 'src/event_queue.c',
         'src/utils.c', 'src/post/fork.c', 'src/vo_driver.c',
#         'src/drivers/yuv2rgb.c', 'src/drivers/yuv2rgb_mmx.c'
]
xineso = Extension('kaa.xine._xinemodule', files, config='src/config.h')
#xineso.libraries += ["X11"]
#xineso.library_dirs.append("/usr/X11R6/lib")

if not xineso.check_library('xine', '1.0.0'):
    print 'xine >= 1.0.0 not found'
    print 'Download from http://xinehq.de'
    sys.exit(1)

setup(module      = 'xine',
      version     = '0.1',
      ext_modules = [ xineso ]
)
