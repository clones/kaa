#if 0
# $Id$
# $Log$
# Revision 1.13  2003/06/09 16:12:47  the_krow
# MPEG Length computation added
#
# Revision 1.12  2003/06/09 14:31:57  the_krow
# fixes on the mpeg parser
# resolutions, fps and bitrate should be reported correctly now
#
# Revision 1.11  2003/06/08 20:28:29  dischi
# bugfix/bugchange, I think it was an endless loop
#
# Revision 1.10  2003/06/08 19:53:21  dischi
# also give the filename to init for additional data tests
#
# Revision 1.9  2003/06/08 13:44:58  dischi
# Changed all imports to use the complete mmpython path for mediainfo
#
# Revision 1.8  2003/06/08 13:11:38  dischi
# removed print at the end and moved it into register
#
# Revision 1.7  2003/06/07 22:54:29  the_krow
# AVInfo stuff added.
#
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
import string
import fourcc

from mmpython import mediainfo

##------------------------------------------------------------------------
## START_CODE
##
## Start Codes, with 'slice' occupying 0x01..0xAF
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
## START CODES
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

##------------------------------------------------------------------------
## FRAME_RATE
##
## A lookup table of all the standard frame rates.  Some rates adhere to
## a particular profile that ensures compatibility with VLSI capabilities
## of the early to mid 1990s.
##
## CPB
##   Constrained Parameters Bitstreams, an MPEG-1 set of sampling and 
##   bitstream parameters designed to normalize decoder computational 
##   complexity, buffer size, and memory bandwidth while still addressing 
##   the widest possible range of applications.
##
## Main Level
##   MPEG-2 Video Main Profile and Main Level is analogous to MPEG-1's 
##   CPB, with sampling limits at CCIR 601 parameters (720x480x30 Hz or 
##   720x576x24 Hz). 
##
##------------------------------------------------------------------------ 
FRAME_RATE = [ 
      0, 
      24000/1001, ## 3-2 pulldown NTSC                    (CPB/Main Level)
      24,         ## Film                                 (CPB/Main Level)
      25,         ## PAL/SECAM or 625/60 video
      30000/1001, ## NTSC                                 (CPB/Main Level)
      30,         ## drop-frame NTSC or component 525/60  (CPB/Main Level)
      50,         ## double-rate PAL
      60000/1001, ## double-rate NTSC
      60,         ## double-rate, drop-frame NTSC/component 525/60 video
      ]

##------------------------------------------------------------------------
## ASPECT_RATIO -- INCOMPLETE?
##
## This lookup table maps the header aspect ratio index to a common name.
## These are just the defined ratios for CPB I believe.  As I understand 
## it, a stream that doesn't adhere to one of these aspect ratios is
## technically considered non-compliant.
##------------------------------------------------------------------------ 
ASPECT_RATIO = [ 'Forbidden',
		      '1/1 (VGA)',
		      '4/3 (TV)',
		      '16/9 (Large TV)',
		      '2.21/1 (Cinema)',
	       ]
 

class MpegInfo(mediainfo.AVInfo):
    def __init__(self,file,filename):
        mediainfo.AVInfo.__init__(self)
        self.context = 'video'
        self.offset = 0
        self.valid = self.isVideo(file) 
        if self.valid:       
            self.mime = 'video/mpeg'
            self.type = 'mpeg video'
            vi = mediainfo.VideoInfo()
            vi.width, vi.height = self.dxy(file)
            vi.fps, aspect = self.framerate_aspect(file)
            vi.bitrate = self.bitrate(file)
            vi.length = self.mpgsize(file) * 8 / vi.bitrate
            self.video.append(vi)

    def dxy(self,file):  
        file.seek(self.offset+4,0)
        v = file.read(4)
        x = struct.unpack('>H',v[:2])[0] >> 4
        y = struct.unpack('>H',v[1:3])[0] & 0x0FFF
        return (x,y)
        
    def framerate_aspect(self,file):
        file.seek(self.offset+7,0)
        v = struct.unpack( '>B', file.read(1) )[0] 
        try:
            fps = FRAME_RATE[v&0xf]
        except IndexError:
            fps = None
        try:
            aspect = ASPECT_RATIO[v>>4]
        except IndexError:
            print v>>4
            aspect = None
        return (fps, aspect)
        
    ##------------------------------------------------------------------------
    ## bitrate()
    ##
    ## From the MPEG-2.2 spec:
    ##
    ##   bit_rate -- This is a 30-bit integer.  The lower 18 bits of the 
    ##   integer are in bit_rate_value and the upper 12 bits are in 
    ##   bit_rate_extension.  The 30-bit integer specifies the bitrate of the 
    ##   bitstream measured in units of 400 bits/second, rounded upwards. 
    ##   The value zero is forbidden.
    ##
    ## So ignoring all the variable bitrate stuff for now, this 30 bit integer
    ## multiplied times 400 bits/sec should give the rate in bits/sec.
    ##  
    ## TODO: Variable bitrates?  I need one that implements this.
    ## 
    ## Continued from the MPEG-2.2 spec:
    ##
    ##   If the bitstream is a constant bitrate stream, the bitrate specified 
    ##   is the actual rate of operation of the VBV specified in annex C.  If 
    ##   the bitstream is a variable bitrate stream, the STD specifications in 
    ##   ISO/IEC 13818-1 supersede the VBV, and the bitrate specified here is 
    ##   used to dimension the transport stream STD (2.4.2 in ITU-T Rec. xxx | 
    ##   ISO/IEC 13818-1), or the program stream STD (2.4.5 in ITU-T Rec. xxx | 
    ##   ISO/IEC 13818-1).
    ## 
    ##   If the bitstream is not a constant rate bitstream the vbv_delay 
    ##   field shall have the value FFFF in hexadecimal.
    ##
    ##   Given the value encoded in the bitrate field, the bitstream shall be 
    ##   generated so that the video encoding and the worst case multiplex 
    ##   jitter do not cause STD buffer overflow or underflow.
    ##
    ##
    ##------------------------------------------------------------------------ 
    def bitrate(self,file):
        file.seek(self.offset+8,0)
        t,b = struct.unpack( '>HB', file.read(3) )
        vrate = t << 2 | b >> 6
        return vrate * 400
        
    def mpgsize(self,file):
        file.seek(0,2)
        return file.tell()
    
    def isVideo(self,file):
        buffer = file.read(10000)
        self.offset = buffer.find( '\x00\x00\x01\xB3' )
        if self.offset >= 0:
            return 1
        return 0

factory = mediainfo.get_singleton()  
factory.register( 'video/mpeg', ('mpeg','mpg','mp4'), mediainfo.TYPE_AV, MpegInfo )
