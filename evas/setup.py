# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.evas
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.evas - An evas wrapper for Python
# Copyright (C) 2006 Jason Tackaberry <tack@sault.org>
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
import sys

try:
    # kaa base imports
    from kaa.distribution import *
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)
    
files = ["src/evas.c", "src/object.c", "src/image.c", "src/text.c", 
         'src/gradient.c', "src/engine_buffer.c", 'src/textblock.c']
evasso = Extension('kaa.evas._evasmodule', files, config='src/config.h')

if not evasso.check_library('evas', '0.9.9.032'):
    print 'Evas >= 0.9.9.032 not found'
    print 'Download from http://enlightenment.freedesktop.org/'
    sys.exit(1)

evasso.config('#define BENCHMARK')
evasso.config('#define EVAS_API_VERSION %d' % evasso.get_library('evas').get_numeric_version())
setup(module      = 'evas',
      version     = '0.1',
      ext_modules = [ evasso ]
)
