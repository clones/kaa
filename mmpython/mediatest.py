#!/usr/bin/python
#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.23  2003/06/20 19:57:30  the_krow
# GNU Header
#
#
# -----------------------------------------------------------------------
# MMPython - Media Metadata for Python
# Copyright (C) 2003 Thomas Schueppel
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
# -----------------------------------------------------------------------
#endif


import sys
sys.path = ['..'] + sys.path

import mmpython

# Usage:
# mediatest files

# files can be a normal file, a device for VCD/VCD/AudioCD or a cd-url
# cd://device:mountpoint:file, e.g. for bla.avi:
# cd:///dev/cdrom:/mnt/cdrom:bla.avi

# To use the cache, make sure /tmp/mmpython exists
# DVD/VCD/AudioCDs are cached with this proram when USE_CACHE == 1

USE_CACHE = 0

if USE_CACHE:
    mmpython.use_cache('./cache')

for file in sys.argv[1:]:
    medium = mmpython.parse(file)
    print "filename : %s" % file

    if medium:
        print "medium is: %s" % medium.type
        print medium
        print
        print
    else:
        print "No Match found"


    if USE_CACHE:
        mmpython.cache_disc(medium)
    
