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
    from kaa.distribution import *
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# config file
config = ConfigFile('src/config.h')

check_library('X11', ['<X11/Xlib.h>'], '')
check_library('imlib2', '1.1.1')
check_library('evas', '0.9.9.010')
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


evas_engines = []
if get_library('evas'):
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
            return 0;
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
        else:
            config.define("USE_EVAS")
            for line in output.splitlines():
                engine = line.strip()
                config.define("ENABLE_ENGINE_%s" % engine.upper())
                evas_engines.append(engine)
                if engine == "gl_x11":
                    # Determine if libGL.so is linked to evas (this is not
                    # the case with recent evas); if not, we must link
                    # explicitly to libGL.
                    evas_gl_linked = os.system("ldd %s | grep -q libGL.so" % out) == 0

        os.unlink(out)


# extention modules
modules = []

if get_library('imlib2'):
    config.define('USE_IMLIB2')

if get_library('X11'):

    # the display so module
    x11 = Extension('kaa.display._X11module',
                    [ 'src/display.c', 'src/x11display.c', 'src/x11window.c',
                      'src/imlib2.c', 'src/evas.c' ],
                    libraries = ['png', 'rt'])

    config.define('HAVE_X11')
    features = []
    if get_library('imlib2') and 'X11' in get_library('imlib2').libraries:
        config.define('USE_IMLIB2_X11')
        x11.add_library('imlib2')
        features.append('imlib2')
    if 'software_x11' in evas_engines:
        features.append('evas')
        x11.add_library('evas')
    if 'gl_x11' in evas_engines:
        features.append('evasGL')
        x11.add_library('evas')
        if not evas_gl_linked:
            x11.libraries.append("GL")
    if not features:
        features = [ 'yes' ]
        get_library('X11').libraries.append('X11')
        x11.add_library('X11')
    else:
        print "+ X11 (%s)" % ', '.join(features)
    modules.append(x11)
else:
    print '- X11'


if get_library('imlib2'):

    # the framebuffer so module
    fb = Extension('kaa.display._FBmodule', [ 'src/fb.c'] )
    fb.add_library('imlib2')
    if 'fb' in evas_engines:
        fb.add_library('evas')
        print "+ Framebuffer (imlib2, evas)"
    else:
        print "+ Framebuffer (imlib2)"
    modules.append(fb)
else:
    print "- Framebuffer"


if get_library('directfb'):

    # the dfb so module
    dfb = Extension('kaa.display._DFBmodule', [ 'src/dfb.c'] )
    dfb.add_library('directfb')
    if 'directfb' in evas_engines:
        print "+ DirectFB (evas)"
        dfb.add_library('evas')
    else:
        print "+ DirectFB"
    modules.append(dfb)
else:
    print "- DirectFB"


if pygame and get_library('sdl') and get_library('imlib2'):

    # pygame module
    sdl = Extension('kaa.display._SDLmodule', ['src/sdl.c'])
    sdl.add_library('imlib2')
    sdl.add_library('sdl')
    sdl.include_dirs.append(pygame)
    modules.append(sdl)
    print "+ SDL (imlib2)"
else:
    print "- SDL"


setup(module  = 'display',
      version = '0.1',
      ext_modules = modules
)

config.unlink()
