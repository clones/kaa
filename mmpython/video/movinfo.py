#if 0
# $Id$
# $Log$
# Revision 1.2  2003/05/13 12:31:43  the_krow
# + Copyright Notice
#
#
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

import re
import struct
import mediainfo
import string
import fourcc


class MovInfo(mediainfo.VideoInfo):
    def __init__(self,file):
        mediainfo.VideoInfo.__init__(self)
        self.context = 'video'
        self.valid = 0
        self.mime = 'video/quicktime'
        self.type = 'Quicktime Video'
        h = file.read(8)
        (type1,type2) = struct.unpack('<II',h)
        if ( type2 == 0x6d6f6f76 ) or ( type2 == 0x6d646174 ) or ( type2 == 0x706e6f74 ):
            self.valid = 1


factory = mediainfo.get_singleton()  
movinfo = MovInfo
factory.register( 'video/quicktime', ['mov', 'qt'], mediainfo.TYPE_VIDEO, movinfo )
print "Quicktime video type registered"
