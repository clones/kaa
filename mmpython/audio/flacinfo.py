#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.2  2003/08/26 21:21:18  outlyer
# Fix two more Python 2.3 warnings.
#
# Revision 1.1  2003/08/18 13:39:52  the_krow
# Initial Import. Started on frame parsing.
#
# -----------------------------------------------------------------------
# MMPython - Media Metadata for Python
# Copyright (C) 2003 Thomas Schueppel, et. al
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

from mmpython import mediainfo
import mmpython


class FlacInfo(mediainfo.MusicInfo):
    def __init__(self,file):
        mediainfo.MusicInfo.__init__(self)
        if file.read(4) != 'fLaC':
            self.valid = 0
            return
        while 1:
            blockheader = file.read(4)
            type = blockheader >> 24 & 0x7F
            if type == 0:
                # STREAMINFO
                pass
            elif type == 1:
                # PADDING
                pass            
            elif type == 1:
                # APPLICATION 
                pass            
            elif type == 1:
                # SEEKTABLE 
                pass            
            elif type == 1:
                # VORBIS_COMMENT 
                pass            
            elif type == 1:
                # CUESHEET 
                pass
            else:
                # UNKNOWN TYPE
                pass
            numbytes = blockheader & 0xFFFFFF
            if blockheader & 0x80000000L == 0x80000000L:
                break
                
                
mmpython.registertype( 'application/flac', ('flac',), mediainfo.TYPE_MUSIC, FlacInfo )                
