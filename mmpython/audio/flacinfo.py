#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.3  2003/08/27 02:53:48  outlyer
# Still doesn't do anything, but at least compiles now; problem is I don't
# know how to conver the endian "headers" in to the types we expect, and I'm
# hardly an expert on binary data.
#
# But I flushed out the header types from the FLAC documentation and
# hopefully Thomas will know what to do...
#
# I can provide a FLAC file if necessary...
#
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
import mmpython.audio.ogginfo as ogginfo
import mmpython


class FlacInfo(mediainfo.MusicInfo):
    def __init__(self,file):
        mediainfo.MusicInfo.__init__(self)
        if file.read(4) != 'fLaC':
            self.valid = 0
            return
        while 1:
            import struct
            (blockheader,) = struct.unpack('>i',file.read(4))
            type = blockheader >> 24 & 0x7F
            print type

            if type == 0:
                # STREAMINFO
                pass
            elif type == 1:
                # PADDING
                pass            
            elif type == 2:
                # APPLICATION 
                pass            
            elif type == 3:
                # SEEKTABLE 
                pass            
            elif type == 4:
                # VORBIS_COMMENT 
                print "Found comment"
                pass            
            elif type == 5:
                # CUESHEET 
                pass
            else:
                # UNKNOWN TYPE
                pass
            numbytes = blockheader & 0xFFFFFF
            if blockheader & 0x80000000L == 0x80000000L:
                break
                
                
mmpython.registertype( 'application/flac', ('flac',), mediainfo.TYPE_MUSIC, FlacInfo )                
