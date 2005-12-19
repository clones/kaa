# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.evas
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
    
files = ["src/evas.c", "src/object.c", "src/image.c", "src/text.c", 
         'src/gradient.c', "src/engine_buffer.c", 'src/textblock.c']
evasso = Extension('kaa.evas._evasmodule', files, config='src/config.h')


if not evasso.check_library('evas', '0.9.9.010'):
    print 'Evas >= 0.9.9.010 not found'
    print 'Download from http://enlightenment.freedesktop.org/'
    sys.exit(1)

setup(module      = 'evas',
      version     = '0.1',
      ext_modules = [ evasso ]
)
