# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.record
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2005 Sönke Schwardt, Dirk Meyer
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
import sys

try:
    # kaa base imports
    from kaa.distribution.core import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# dvb module
dvb = Extension('kaa.record._dvb', [ 'src/dvb_tuner.cc', 'src/dvb_device.cc' ])

# fdsplitter module
fdsplitter = Extension('kaa.record._fdsplitter', [ 'src/fdsplitter.cc' ] )

# filter module
files = [ 'src/fp_filewriter.cc', 'src/fp_remux.cc', 'src/fp_udpsend.cc',
          'src/remux.cc', 'src/ringbuffer.cc', 'src/filter.cc']
filter = Extension('kaa.record._filter', files)

# list of all modules
ext_modules = [ dvb, filter, fdsplitter ]

# vbi module
vbi = Extension('kaa.record._vbi', ['src/vbi.cc'])
if not vbi.check_cc(['"libzvbi.h"'], '', '-lzvbi'):
    print 'libzvbi not found, disable vbi support'
else:
    vbi.libraries.append('zvbi')
    ext_modules.append(vbi)
    
setup(module      = 'record',
      version     = '0.1.0',
      license     = 'GPL',
      summary     = 'Python library for recording from different types of tv cards to different outputs.',
      rpminfo     = {
          'requires':       'python-kaa-base >= 0.1.2',
          'build_requires': 'python-kaa-base >= 0.1.2'
      },
      ext_modules = ext_modules
)
