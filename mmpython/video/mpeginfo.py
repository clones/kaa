#if 0
# $Id$
# $Log$
# Revision 1.6  2003/06/07 22:30:21  the_krow
# added new avinfo structure
#
# Revision 1.4  2003/05/13 17:49:42  the_krow
# IPTC restructured\nEXIF Height read correctly\nJPEG Endmarker read
#
# Revision 1.3  2003/05/13 12:31:43  the_krow
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

##------------------------------------------------------------------------
## START_CODE
##
## Start Codes, with 'slice' occupying 0x01..0xAF
## No inlining here but easy lookups when codes are encountered.  Only
## really useful for debugging or dumping the bitstream structure.
##------------------------------------------------------------------------
START_CODE = {
    0x00 : 'picture_start_code',
    0xB0 : 'reserved',
    0xB1 : 'reserved',
    0xB2 : 'user_data_start_code',
    0xB3 : 'sequence_header_code',
    0xB4 : 'sequence_error_code',
    0xB5 : 'extension_start_code',
    0xB6 : 'reserved',
    0xB7 : 'sequence end',
    0xB8 : 'group of pictures',
}
for i in range(0x01,0xAF): 
    START_CODE[i] = 'slice_start_code'

##------------------------------------------------------------------------
## INLINED START CODES
##
## These should get inlined for a big speed boost.  We should only need
## these codes.
##------------------------------------------------------------------------
PICTURE   = 0x00
USERDATA  = 0xB2
SEQ_HEAD  = 0xB3
SEQ_ERR   = 0xB4
EXT_START = 0xB5
SEQ_END   = 0xB7
GOP       = 0xB8

SEQ_START_CODE = 0xB3
PACK_PKT       = 0xBA
SYS_PKT        = 0xBB
PADDING_PKT    = 0xBE
AUDIO_PKT      = 0xC0
VIDEO_PKT      = 0xE0




class MpegInfo(mediainfo.AVInfo):
    def __init__(self,file):
        mediainfo.AVInfo.__init__(self)
        self.context = 'video'
        self.offset = 0
        self.valid = self.isVideo(file) 
        if self.valid:       
            self.mime = 'video/mpeg'
            self.type = 'mpeg video'
            self.dxy(file)
            print "%d x %d" % ( self.width, self.height )
        else:
            return

    def dxy(self,file):  
        print self.offset
        file.seek(self.offset+4,0)
        v = file.read(4)
        self.width = struct.unpack('>H',v[:2])[0] >> 4
        self.height = struct.unpack('>H',v[1:3])[0] & 0x0FFF

    def isVideo(self,file):
        buffer = file.read(4000)
        self.offset = 0
        while ( self.offset <= len(buffer) - 4 ):
            a = ord(buffer[self.offset])
            if a != 0:
                self.offset += 1
                continue
            b = ord(buffer[self.offset+1])
            if b != 0:
                self.offset += 2
                continue
            c = ord(buffer[self.offset+2])
            if c != 1:
                continue
            d = ord(buffer[self.offset+3])
            if ( d == SEQ_START_CODE ):
	        return 1
	    elif ( self.context == 'video' ) and ( d == SYS_PKT ):
	        print "videocontext"
	        return 0
            self.offset += 1
        return 0

factory = mediainfo.get_singleton()  
mpginfo = MpegInfo
factory.register( 'video/mpeg', ('mpeg','mpg','mp4'), mediainfo.TYPE_AV, mpginfo )
print "mpeg video type registered"
