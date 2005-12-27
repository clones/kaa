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
    from kaa.base.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# the framebuffer so module
fb = Extension('kaa.display._FBmodule', [ 'src/fb.c'] )

if fb.check_library('imlib2', '1.1.1'):
    print "+ FB support enabled"
else:
    print "+ FB support disabled"
    fb = None

# the display so module
display = Extension('kaa.display._Displaymodule',
                    [ 'src/display.c', 'src/sdl.c', 'src/x11display.c',
                      'src/x11window.c', 'src/imlib2.c', 'src/evas.c' ],
                    libraries = ['png', 'rt'],
                    config='src/config.h')


if display.check_library('imlib2', '1.1.1'):
    display.config('#define USE_IMLIB2')
    if 'X11' in display.libraries:
        display.config('#define USE_IMLIB2_DISPLAY')
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
    if not display.check_library('sdl', '1.2.5'):
        print 'SDL not found'
        raise ImportError
    display.include_dirs.append(inc)
    display.config('#define USE_PYGAME\n')
    print "+ pygame support enabled"
except ImportError:
    print '- pygame support disabled'

# Test for evas and supported engines
evas_engines = ""
if display.check_library('evas', '0.9.9.010'):
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
            if engine == "software_x11":
                display.config("#define ENABLE_ENGINE_SOFTWARE_X11\n")
                evas_engines += " software_x11"
            elif engine == "gl_x11":
                display.config("#define ENABLE_ENGINE_GL_X11\n")
                evas_engines += " gl_x11"
            elif engine == 'fb':
                display.config("#define ENABLE_ENGINE_FB\n")
                evas_engines += " fb"
                # FIXME: This is ugly. Find a better way to add
                # the evas libs to the fb module
                fb.libraries += display.libraries
                fb.library_dirs += display.library_dirs
        os.unlink(out)

if evas_engines == "":
    print "- evas support disabled"
else:
    print "+ evas support enabled for engines:" + evas_engines
    display.config("#define USE_EVAS\n")

ext_modules = [ display ]
if fb:
    ext_modules.append(fb)
    
setup(module  = 'display',
      version = '0.1',
      ext_modules = ext_modules
)
