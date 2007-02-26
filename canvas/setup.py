# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.canvas
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-canvas - Second generation Canvas System using Evas as backend
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
#
# First Edition: Jason Tackaberry <tack@sault.org>
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
    from kaa.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)
    
ext_modules = []
mng = Extension("kaa.canvas._mng", ['src/extensions/mng.c'])
if mng.check_cc(["<libmng.h>"], "", "-lmng"):
    ext_modules.append(mng)
    mng.libraries.append("mng")
    print "+ mng support enabled"
else:
    print "- mng support disabled"

svg = Extension("kaa.canvas._svg", ['src/extensions/svg.c'])
if svg.check_library("librsvg-2.0", "2.10.0"):
    ext_modules.append(svg)
    print "+ svg support enabled"
else:
    print "- svg support disabled"


setup(module = 'canvas', 
      version = '0.5.0', 
      license = 'LGPL',
      summary = 'High-level canvas API built on top of kaa.evas',
      rpminfo = {
          'requires':       'python-kaa-base >= 0.1.2, python-kaa-evas >= 0.1.0, python-kaa-imlib2 >= 0.2.0,' \
                            'librsvg2 >= 2.9.0, libmng >= 1.0.9',
          'build_requires': 'python-kaa-base >= 0.1.2, librsvg2-devel >= 2.9.0, libmng-devel >= 1.0.9'
      },
      ext_modules = ext_modules)
