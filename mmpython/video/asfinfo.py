#if 0
# $Id$
# $Log$
# Revision 1.4  2003/06/08 13:44:58  dischi
# Changed all imports to use the complete mmpython path for mediainfo
#
# Revision 1.3  2003/06/08 13:11:38  dischi
# removed print at the end and moved it into register
#
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
import string
import fourcc

from mmpython import mediainfo

class AsfInfo(mediainfo.VideoInfo):
    def __init__(self,file):
        mediainfo.VideoInfo.__init__(self)
        self.context = 'video'
        self.valid = 0
        self.mime = 'video/asf'
        self.type = 'asf video'
        h = file.read(8)
        (type1,type2) = struct.unpack('<II',h)
        if ( type1 == 0x3026b275 ) or ( type1 == 0x75b22630 ):
            self.valid = 1


factory = mediainfo.get_singleton()  
factory.register( 'video/asf', ['asf'], mediainfo.TYPE_VIDEO, AsfInfo )
