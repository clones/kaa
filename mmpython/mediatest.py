#!/usr/bin/python
#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.28  2004/01/27 20:28:57  dischi
# remove cache, it does not belong in mmpython
#
# Revision 1.27  2003/07/19 11:38:19  dischi
# turn off debug as default, some exception handling
#
# Revision 1.26  2003/06/30 13:17:18  the_krow
# o Refactored mediainfo into factory, synchronizedobject
# o Parsers now register directly at mmpython not at mmpython.mediainfo
# o use mmpython.Factory() instead of mmpython.mediainfo.get_singleton()
# o Bugfix in PNG parser
# o Renamed disc.AudioInfo into disc.AudioDiscInfo
# o Renamed disc.DataInfo into disc.DataDiscInfo
#
# Revision 1.25  2003/06/23 09:22:54  the_krow
# Typo and Indentation fixes.
#
# Revision 1.23  2003/06/20 19:57:30  the_krow
# GNU Header
#
#
# -----------------------------------------------------------------------
# MMPython - Media Metadata for Python
# Copyright (C) 2003 Thomas Schueppel, Dirk Meyer
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

from mmpython import *

# Usage:
# mediatest files

# files can be a normal file, a device for VCD/VCD/AudioCD or a cd-url
# cd://device:mountpoint:file, e.g. for bla.avi:
# cd:///dev/cdrom:/mnt/cdrom:bla.avi

# turn on debug
mediainfo.DEBUG = 1
factory.DEBUG   = 1

for file in sys.argv[1:]:
    medium = parse(file)
    print "filename : %s" % file

    if medium:
        print "medium is: %s" % medium.type
        print medium
        print
        print
    else:
        print "No Match found"
