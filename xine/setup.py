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
    from kaa.distribution import *
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# config file
config = ConfigFile('src/config.h')

files = ['src/xine.c', 'src/video_port.c', 'src/audio_port.c', 'src/stream.c',
         'src/post.c', 'src/drivers/video_out_kaa.c',
         'src/post_out.c', 'src/post_in.c', 'src/event.c', 'src/event_queue.c',
         'src/utils.c', 'src/vo_driver.c', 'src/drivers/kaa.c',
         'src/drivers/yuv2rgb.c', 'src/drivers/yuv2rgb_mmx.c', 'src/drivers/dummy.c',
         'src/drivers/video_out_dummy.c', 'src/drivers/common.c', 'src/drivers/fb.c'
        ]


xineso = Extension('kaa.xine._xinemodule', files, extra_compile_args = ['-DPIC'])

if not xineso.check_library('xine', '1.1.1'):
    print 'xine >= 1.1.1 not found'
    print 'Download from http://xinehq.de'
    config.unlink()
    sys.exit(1)

# FIXME: this logic still needs to be smarter
libdirs = ['/usr/X11R6/lib', '/usr/X11R6/lib64', '/usr/lib64', '/usr/lib']
for dir in libdirs:
    # check for X11 in the given directory
    if xineso.check_cc(['<X11/Xlib.h>'], '', '-lX11 -L%s' % dir):
        config.define('HAVE_X11')
        xineso.files.append('src/drivers/x11.c')
        xineso.libraries.append("X11")
        xineso.libraries.append("GL")
        xineso.library_dirs.append(dir)
        print "+ X11 found in %s; X11 support enabled" % dir

        glxtest_code = 'unsigned int count; glXWaitVideoSyncSGI(2, count, &count);'
        if xineso.check_cc(['<GL/glx.h>'], glxtest_code, '-lGL -DGLX_GLXEXT_PROTOTYPES -Werror -L%s' % dir):
            config.define("HAVE_OPENGL_VSYNC")
            print "+ OpenGL vsync support enabled"
        else:
            print "- OpenGL vsync support disabled"
        break
else:
    print "- X11 not found; disabling X11 support."

arch = os.popen("uname -m").read().strip()
if arch == "x86_64":
    config.define('ARCH_X86_64')
elif arch == "i386":
    config.define('ARCH_X86')

requires_common =       'kaa-base >= 0.1.2, kaa-display >= 0.1.0, xine-lib >= 1.1.0'
build_requires_common = 'kaa-base >= 0.1.2, xine-lib-devel >= 1.1.0, python-devel >= 2.4.0'

setup(module      = 'xine',
      version     = '0.9.0',
      license     = 'GPL',
      summary     = 'Python bindings for xine-lib',
      rpminfo     = {
          'requires':       'libX11 >= 1.0.0, mesa-libGL >= 6.5.0, ' + requires_common,
          'build_requires': 'libX11-devel >= 1.0.0, mesa-libGL-devel >= 6.5.0, ' + build_requires_common,
          'fc4': {
              'requires':       'xorg-x11 >= 6.8.0, ' + requires_common,
              'build_requires': 'xorg-x11-devel >= 6.8.0, ' + build_requires_common
          }
      },
      ext_modules = [ xineso ]
)

config.unlink()
