#if 0
# $Id$
# $Log$
# Revision 1.23  2004/06/23 19:44:10  dischi
# better length detection, big cleanup
#
# Revision 1.22  2004/06/22 21:37:34  dischi
# o PES support
# o basic length detection for TS and PES
#
# Revision 1.21  2004/06/21 20:37:34  dischi
# basic support for mpeg-ts
#
# Revision 1.20  2004/03/13 23:41:59  dischi
# add AudioInfo to mpeg for all streams
#
# Revision 1.19  2004/02/11 20:11:54  dischi
# Updated length calculation for mpeg files. This may not work for all files.
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
import os
import struct
import string
import fourcc

from mmpython import mediainfo
import mmpython
import stat

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


TS_PACKET_LENGTH = 188
TS_SYNC          = 0x47

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
      round(24000.0/1001*100)/100, ## 3-2 pulldown NTSC (CPB/Main Level)
      24,           ## Film (CPB/Main Level)
      25,           ## PAL/SECAM or 625/60 video
      round(30000.0/1001*100)/100, ## NTSC (CPB/Main Level)
      30,           ## drop-frame NTSC or component 525/60  (CPB/Main Level)
      50,           ## double-rate PAL
      round(60000.0/1001*100)/100, ## double-rate NTSC
      60,           ## double-rate, drop-frame NTSC/component 525/60 video
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
    def __init__(self,file):
        mediainfo.AVInfo.__init__(self)
        self.context = 'video'
        self.sequence_header_offset = 0

        # detect TS (fast scan)
        self.valid = self.isTS(file) 

        if not self.valid:
            # detect system mpeg (many infos)
            self.valid = self.isMPEG(file) 

        if not self.valid:
            # detect PES
            self.valid = self.isPES(file) 
            
        if self.valid:       
            self.mime = 'video/mpeg'
            if not self.video:
                self.video.append(mediainfo.VideoInfo())

            if self.sequence_header_offset <= 0:
                return

            for vi in self.video:
                vi.width, vi.height = self.dxy(file)
                vi.fps, vi.aspect = self.framerate_aspect(file)
                vi.bitrate = self.bitrate(file)
                if self.length:
                    vi.length = self.length

            if not self.type:
                if self.video[0].width == 480:
                    self.type = 'MPEG2 video' # SVCD spec
                elif self.video[0].width == 352:
                    self.type = 'MPEG1 video' # VCD spec
                else:
                    self.type = 'MPEG video'

            if mediainfo.DEBUG > 2:
                self.__scan__()

            
    def dxy(self,file):  
        file.seek(self.sequence_header_offset+4,0)
        v = file.read(4)
        x = struct.unpack('>H',v[:2])[0] >> 4
        y = struct.unpack('>H',v[1:3])[0] & 0x0FFF
        return (x,y)

        
    def framerate_aspect(self,file):
        file.seek(self.sequence_header_offset+7,0)
        v = struct.unpack( '>B', file.read(1) )[0] 
        try:
            fps = FRAME_RATE[v&0xf]
        except IndexError:
            fps = None
        try:
            aspect = ASPECT_RATIO[v>>4]
        except IndexError:
            if mediainfo.DEBUG:
                print 'Index error: %s' % (v>>4)
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


    ## Some parts in the code are based on mpgtx (mpgtx.sf.net)
    
    def bitrate(self,file):
        file.seek(self.sequence_header_offset+8,0)
        t,b = struct.unpack( '>HB', file.read(3) )
        vrate = t << 2 | b >> 6
        return vrate * 400
        

    def ReadSCRMpeg2(self, buffer):
        """
        read SCR (timestamp) for MPEG2 at the buffer beginning (6 Bytes)
        """
	highbit = (ord(buffer[0])&0x20)>>5

	low4Bytes= ((ord(buffer[0]) & 0x18) >> 3) << 30
	low4Bytes |= (ord(buffer[0]) & 0x03) << 28
	low4Bytes |= ord(buffer[1]) << 20
	low4Bytes |= (ord(buffer[2]) & 0xF8) << 12
	low4Bytes |= (ord(buffer[2]) & 0x03) << 13
	low4Bytes |= ord(buffer[3]) << 5
	low4Bytes |= (ord(buffer[4])) >> 3

	sys_clock_ref=(ord(buffer[4]) & 0x3) << 7
	sys_clock_ref|=(ord(buffer[5]) >> 1)

 	return (long(highbit * (1<<16) * (1<<16)) + low4Bytes) / 90000


    def ReadSCRMpeg1(self, buffer):
        """
        read SCR (timestamp) for MPEG1 at the buffer beginning (5 Bytes)
        """
	highbit = (ord(buffer[0]) >> 3) & 0x01

	low4Bytes = ((ord(buffer[0]) >> 1) & 0x03) << 30
	low4Bytes |= ord(buffer[1]) << 22;
	low4Bytes |= (ord(buffer[2]) >> 1) << 15;
	low4Bytes |= ord(buffer[3]) << 7;
	low4Bytes |= ord(buffer[4]) >> 1;

	return (long(highbit) * (1<<16) * (1<<16) + low4Bytes) / 90000;


    def ReadPTS(self, buffer):
        """
        read PTS (PES timestamp) at the buffer beginning (5 Bytes)
        """
        high = ((ord(buffer[0]) & 0xF) >> 1)
        med  = (ord(buffer[1]) << 7) + (ord(buffer[2]) >> 1)
        low  = (ord(buffer[3]) << 7) + (ord(buffer[4]) >> 1)
        return ((long(high) << 30 ) + (med << 15) + low) / 90000


    def ReadHeader(self, buffer, offset):
        """
        Handle MPEG header in buffer on position offset
        Return -1 on error, new offset or 0 if the new offset can't be scanned
        """
        if buffer[offset:offset+3] != '\x00\x00\x01':
            return -1

        id = ord(buffer[offset+3])

        if id == PADDING_PKT:
            return offset + (ord(buffer[offset+4]) << 8) + ord(buffer[offset+5]) + 6

        if id == PACK_PKT:
            if ord(buffer[offset+4]) & 0xF0 == 0x20:
                self.type     = 'MPEG1 video'
                self.get_time = self.ReadSCRMpeg1
                return offset + 12
            elif (ord(buffer[offset+4]) & 0xC0) == 0x40:
                self.type     = 'MPEG2 video'
                self.get_time = self.ReadSCRMpeg2
                return offset + (ord(buffer[offset+13]) & 0x07) + 14
            else:
                # WTF? Very strange
                return -1

        if 0xC0 <= id <= 0xDF:
            # code for audio stream
            for a in self.audio:
                if a.id == id:
                    break
            else:
                self.audio.append(mediainfo.AudioInfo())
                self.audio[-1].id = id
                self.audio[-1].keys.append('id')
            return 0

        if 0xE0 <= id <= 0xEF:
            # code for video stream
            for v in self.video:
                if v.id == id:
                    break
            else:
                self.video.append(mediainfo.VideoInfo())
                self.video[-1].id = id
                self.video[-1].keys.append('id')
            return 0

        if id == SEQ_HEAD:
            # sequence header, remember that position for later use
            self.sequence_header_offset = offset
            return 0

        return 0


    # Normal MPEG (VCD, SVCD) ========================================
        
    def isMPEG(self, file):
        """
        This MPEG starts with a sequence of 0x00 followed by a PACK Header
        http://dvd.sourceforge.net/dvdinfo/packhdr.html
        """
        file.seek(0,0)
        buffer = file.read(10000)
        offset = 0

        # seek until the 0 byte stop
        while buffer[offset] == '\0':
            offset += 1
        offset -= 2

        # test for mpeg header 0x00 0x00 0x01
        if not buffer[offset:offset+4] == '\x00\x00\x01%s' % chr(PACK_PKT):
            return 0

        # scan the 100000 bytes of data
        buffer += file.read(100000)

        # scan first header, to get basic info about
        # how to read a timestamp
        self.ReadHeader(buffer, offset)

        # store first timestamp
        self.ts_start = self.get_time(buffer[offset+4:])

        while len(buffer) > offset + 1000 and buffer[offset:offset+3] == '\x00\x00\x01':
            # read the mpeg header
            new_offset = self.ReadHeader(buffer, offset)

            # header scanning detected error, this is no mpeg
            if new_offset == -1:
                return 0

            if new_offset:
                # we have a new offset
                offset = new_offset

                # skip padding 0 before a new header
                while not ord(buffer[offset+2]):
                    offset += 1

            else:
                # seek to new header by brute force
                offset += buffer[offset+4:].find('\x00\x00\x01') + 4

        # fill in values for support functions:
        self.__seek_size__   = 1000000
        self.__sample_size__ = 10000
        self.__search__      = self._find_timer_
        self.filename        = file.name

        # get length of the file
        self.length = self.get_length()
        return 1


    def _find_timer_(self, buffer):
        """
        Return position of timer in buffer or -1 if not found.
        This function is valid for 'normal' mpeg files
        """
        pos = buffer.find('\x00\x00\x01%s' % chr(PACK_PKT))
        if pos == -1:
            return -1
        return pos + 4
        


    # PES ============================================================


    def ReadPESHeader(self, offset, buffer):
        """
        Parse a PES header.
        Since it starts with 0x00 0x00 0x01 like 'normal' mpegs, this
        function will return (0, -1) when it is no PES header or
        (packet length, timestamp position (maybe -1))
        
        http://dvd.sourceforge.net/dvdinfo/pes-hdr.html
        """
        if not buffer[0:3] == '\x00\x00\x01':
            return 0, -1

        packet_length = (ord(buffer[4]) << 8) + ord(buffer[5]) + 6
        align         = ord(buffer[6]) & 4
        header_length = ord(buffer[8])

        # PES ID (starting with 001)
        if ord(buffer[3]) & 0xE0 == 0xC0:
            id = ord(buffer[3]) & 0x1F
            type = 'audio'
            for a in self.audio:
                if a.id == id:
                    break
            else:
                self.audio.append(mediainfo.AudioInfo())
                self.audio[-1].id = id
                self.audio[-1].keys.append('id')

        elif ord(buffer[3]) & 0xF0 == 0xE0:
            id = ord(buffer[3]) & 0xF
            type = 'video'
            for v in self.video:
                if v.id == id:
                    break
            else:
                self.video.append(mediainfo.VideoInfo())
                self.video[-1].id = id
                self.video[-1].keys.append('id')

            # new mpeg starting
            if buffer[header_length+9:header_length+13] == \
                   '\x00\x00\x01\xB3' and not self.sequence_header_offset:
                # yes, remember offset for later use
                self.sequence_header_offset = offset + header_length+9
        else:
            # unknown content
            pass

        ptsdts = ord(buffer[7]) >> 6

        if ptsdts and ptsdts == ord(buffer[9]) >> 4:
            # timestamp = self.ReadPTS(buffer[9:14])
            return packet_length, 9
            
        return packet_length, -1
    


    def isPES(self, file):
        if mediainfo.DEBUG:
            print 'trying mpeg-pes scan'
        file.seek(0,0)
        buffer = file.read(3)

        # header (also valid for all mpegs)
        if not buffer == '\x00\x00\x01':
            return 0

        self.sequence_header_offset = 0
        buffer += file.read(10000)

        offset = 0
        while offset + 1000 < len(buffer):
            pos, timestamp = self.ReadPESHeader(offset, buffer[offset:])
            if not pos:
                return 0
            if timestamp != -1 and not hasattr(self, 'ts_start'):
                self.get_time = self.ReadPTS
                self.ts_start = self.get_time(buffer[offset+timestamp:offset+timestamp+5])
            if self.sequence_header_offset and hasattr(self, 'ts_start'):
                # we have all informations we need
                break

            offset += pos
            if offset + 1000 < len(buffer) and len(buffer) < 1000000 or 1:
                # looks like a pes, read more
                buffer += file.read(10000)
        
        if not self.video and not self.audio:
            # no video and no audio? 
            return 0

        self.type = 'MPEG-PES'

        # fill in values for support functions:
        self.__seek_size__   = 10000000  # 10 MB
        self.__sample_size__ = 500000    # 500 k scanning
        self.__search__      = self._find_timer_PES_
        self.filename        = file.name

        # get length of the file
        self.length = self.get_length()
        return 1


    def _find_timer_PES_(self, buffer):
        """
        Return position of timer in buffer or -1 if not found.
        This function is valid for PES files
        """
        pos    = buffer.find('\x00\x00\x01')
        offset = 0
        if pos == -1 or offset + 1000 >= len(buffer):
            return -1
        
        retpos   = -1
        ackcount = 0
        while offset + 1000 < len(buffer):
            pos, timestamp = self.ReadPESHeader(offset, buffer[offset:])
            if timestamp != -1 and retpos == -1:
                retpos = offset + timestamp
            if pos == 0:
                # Oops, that was a mpeg header, no PES header
                offset  += buffer[offset:].find('\x00\x00\x01')
                retpos   = -1
                ackcount = 0
            else:
                offset   += pos
                ackcount += 1
            if ackcount > 10:
                # looks ok to me
                return retpos
        return -1
            

    # Transport Stream ===============================================
    
    def isTS(self, file):
        file.seek(0,0)

        buffer = file.read(TS_PACKET_LENGTH * 2)
        c = 0

        while c + TS_PACKET_LENGTH < len(buffer):
            if ord(buffer[c]) == ord(buffer[c+TS_PACKET_LENGTH]) == TS_SYNC:
                break
            c += 1
        else:
            return 0

        buffer += file.read(1000000)
        self.type = 'MPEG-TS'

        while c + TS_PACKET_LENGTH < len(buffer):
            start = ord(buffer[c+1]) & 0x40
            if not start:
                c += TS_PACKET_LENGTH
                continue

            tsid = ((ord(buffer[c+1]) & 0x3F) << 8) + ord(buffer[c+2])
            adapt = (ord(buffer[c+3]) & 0x30) >> 4

            offset = 4
            if adapt & 0x02:
                # meta info present, skip it for now
                offset += ord(buffer[c+offset]) + 1

            if adapt & 0x01:
                # PES
                timestamp = self.ReadPESHeader(c+offset, buffer[c+offset:])[1]
                if timestamp != -1 and not hasattr(self, 'ts_start'):
                    self.get_time = self.ReadPTS
                    timestamp     = c + offset + timestamp
                    self.ts_start = self.get_time(buffer[timestamp:timestamp+5])

            elif adapt & 0x01:
                # no PES, scan for something else here
                pass
            
            c += TS_PACKET_LENGTH

        if not self.sequence_header_offset:
            return 0

        # fill in values for support functions:
        self.__seek_size__   = 10000000  # 10 MB
        self.__sample_size__ = 100000    # 100 k scanning
        self.__search__      = self._find_timer_TS_
        self.filename        = file.name

        # get length of the file
        self.length = self.get_length()
        return 1


    def _find_timer_TS_(self, buffer):
        c = 0

        while c + TS_PACKET_LENGTH < len(buffer):
            if ord(buffer[c]) == ord(buffer[c+TS_PACKET_LENGTH]) == TS_SYNC:
                break
            c += 1
        else:
            return -1
        
        while c + TS_PACKET_LENGTH < len(buffer):
            start = ord(buffer[c+1]) & 0x40
            if not start:
                c += TS_PACKET_LENGTH
                continue

            adapt = (ord(buffer[c+3]) & 0x30) >> 4

            offset = 4
            if adapt & 0x02:
                # meta info present, skip it for now
                offset += ord(buffer[c+offset]) + 1

            if adapt & 0x01:
                timestamp = self.ReadPESHeader(c+offset, buffer[c+offset:])[1]
                return c + offset + timestamp
            c += TS_PACKET_LENGTH
        return -1



    # Support functions ==============================================

    def get_endpos(self):
        """
        get the last timestamp of the mpeg, return -1 if this is not possible
        """
        if not hasattr(self, 'filename') or not hasattr(self, 'ts_start'):
            return -1

        file = open(self.filename)
        file.seek(os.stat(self.filename)[stat.ST_SIZE]-self.__sample_size__)
        buffer = file.read(self.__sample_size__)

        end = -1
        while 1:
            pos = self.__search__(buffer)
            if pos == -1:
                break
            end    = self.get_time(buffer[pos:])
            buffer = buffer[pos+100:]
            
        file.close()
        return end
    

    def get_length(self):
        """
        get the length in seconds, return -1 if this is not possible
        """
        end = self.get_endpos()
        if end == -1 or self.ts_start > end:
            return -1
        return end - self.ts_start
    

    def seek(self, end_time):
        """
        Return the byte position in the file where the time position
        is 'pos' seconds. Return 0 if this is not possible
        """
        if not hasattr(self, 'filename') or not hasattr(self, 'ts_start'):
            return 0

        file    = open(self.filename)
        seek_to = 0
        
        while 1:
            file.seek(self.__seek_size__, 1)
            buffer = file.read(self.__sample_size__)
            if len(buffer) < 10000:
                break
            pos = self.__search__(buffer)
            if pos != -1:
                # found something
                if self.get_time(buffer[pos:]) >= end_time:
                    # too much, break
                    break
            # that wasn't enough
            seek_to = file.tell()

        file.close()
        return seek_to


    def __scan__(self):
        """
        scan file for timestamps (may take a long time)
        """
        if not hasattr(self, 'filename') or not hasattr(self, 'ts_start'):
            return 0
        file = open(self.filename)
        print 'scanning file...'
        while 1:
            file.seek(self.__seek_size__ * 10, 1)
            buffer = file.read(self.__sample_size__)
            if len(buffer) < 10000:
                break
            pos = self.__search__(buffer)
            if pos == -1:
                continue
            print self.get_time(buffer[pos:])

        file.close()
        print 'done'
        print

    
    
mmpython.registertype( 'video/mpeg', ('mpeg','mpg','mp4', 'ts'), mediainfo.TYPE_AV, MpegInfo )
