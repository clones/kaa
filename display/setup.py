# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.display
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-display - X11/SDL Display module
# Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
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
import re
import os
import sys
import popen2

try:
    # kaa base imports
    from kaa.base.distribution import Extension, Configfile, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# a list of all modules
modules = []

# the framebuffer so module
fb = Extension('kaa.display._FBmodule', [ 'src/fb.c'] )

if fb.check_library('imlib2', '1.1.1'):
    print "+ FB support enabled"
    modules.append(fb)
else:
    print "+ FB support disabled"
    fb = None

# the framebuffer so module
dfb = Extension('kaa.display._DFBmodule', [ 'src/dfb.c'] )

if dfb.check_library('directfb', '0.9.20'):
    print "+ DFB support enabled"
    modules.append(dfb)
else:
    print "+ DFB support disabled"
    dfb = None

# config file
config = Configfile('src/config.h')

# the display so module
x11 = Extension('kaa.display._Displaymodule',
                [ 'src/display.c', 'src/sdl.c', 'src/x11display.c',
                  'src/x11window.c', 'src/imlib2.c', 'src/evas.c' ],
                libraries = ['png', 'rt'])

# check if X11 is actually present
if not x11.check_cc(['<X11/Xlib.h>'], '', '-lX11'):
    print "System without X11 detected! Disabling all X11 dependencies..."
    x11 = None
else:
    modules.append(x11)
    config.define('HAVE_X11')

    if x11.check_library('imlib2', '1.1.1'):
        config.define('USE_IMLIB2')
        if 'X11' in x11.libraries:
            config.define('USE_IMLIB2_DISPLAY')
            print "+ Imlib2 support enabled"
        else:
            print '- Imlib2 compiled without X11, not building imlib2 display'
    else:
        print "- Imlib2 support disabled."

    try:
        # test for pygame support
        try:
            import pygame
        except ImportError, e:
            print 'pygame module not found'
            raise e
        inc = re.sub("/(lib|lib64)/", "/include/",
                     pygame.__path__[0]).replace("site-packages/", "")
        if not os.path.isdir(inc):
            print 'pygame header file not found. Install pygame-devel.'
            raise ImportError
        if not x11.check_library('sdl', '1.2.5'):
            print 'SDL not found'
            raise ImportError
        x11.include_dirs.append(inc)
        config.define('USE_PYGAME\n')
        print "+ pygame support enabled"
    except ImportError:
        print '- pygame support disabled'


# Test for evas and supported engines
evas_engines = ""
for display in modules:
    if not display.check_library('evas', '0.9.9.010'):
        break
else:
    indent = re.compile("^", re.M)
    out = "/tmp/a.out.%s" % os.getpid()
    cmd = "cc -x c - `evas-config --libs --cflags` -o %s" % out
    p = popen2.Popen4(cmd)
    p.tochild.write('''
        #include <Evas.h>
        #include <stdio.h>

        int main(int argc, char **argv) {
            Evas_List *p = evas_render_method_list();
            for (;p; p = p->next) printf("%s\\n", (char *)p->data);
        }
    ''')
    p.tochild.close()
    output = p.fromchild.read()
    if os.waitpid(p.pid, 0)[1] != 0:
        output = indent.sub("\t", output)
        print "! Failed to compile evas test program:\n", output
    else:
        p = popen2.Popen4(out)
        output = p.fromchild.read()
        if os.waitpid(p.pid, 0)[1] != 0:
            output = indent.sub("\t", output)
            print "! Failed to run evas test program:\n", output

        for line in output.splitlines():
            engine = line.strip()
            if engine == "software_x11" and x11:
                config.define("ENABLE_ENGINE_SOFTWARE_X11")
                evas_engines += " software_x11"
            elif engine == "gl_x11" and x11:
                config.define("ENABLE_ENGINE_GL_X11")
                evas_engines += " gl_x11"
            elif engine == 'fb' and fb:
                config.define("ENABLE_ENGINE_FB")
                evas_engines += " fb"
            elif engine == 'directfb' and dfb:
                config.define("ENABLE_ENGINE_DFB")
                evas_engines += " dfb"
        os.unlink(out)

if evas_engines == "":
    print "- evas support disabled"
else:
    print "+ evas support enabled for engines:" + evas_engines
    config.define("USE_EVAS")

setup(module  = 'display',
      version = '0.1',
      ext_modules = modules
)

config.unlink()
