#if 0
# -----------------------------------------------------------------------
# ogminfo.py - Ogg Streaming Video Files
# -----------------------------------------------------------------------
# $Id$
#
# $Log$
# Revision 1.7  2003/06/30 13:17:20  the_krow
# o Refactored mediainfo into factory, synchronizedobject
# o Parsers now register directly at mmpython not at mmpython.mediainfo
# o use mmpython.Factory() instead of mmpython.mediainfo.get_singleton()
# o Bugfix in PNG parser
# o Renamed disc.AudioInfo into disc.AudioDiscInfo
# o Renamed disc.DataInfo into disc.DataDiscInfo
#
# Revision 1.6  2003/06/29 12:11:16  dischi
# changed print to _print
#
# Revision 1.5  2003/06/23 20:48:11  the_krow
# width + height fixes for OGM files
#
# Revision 1.4  2003/06/23 13:20:51  the_krow
# basic parsing should now work.
#
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


from mmpython import mediainfo
import mmpython
import struct
import re

PACKET_TYPE_HEADER =  0x01
PACKED_TYPE_METADATA = 0x03
PACKED_TYPE_SETUP = 0x05
PACKET_TYPE_BITS =    0x07
PACKET_IS_SYNCPOINT = 0x08

#VORBIS_VIDEO_PACKET_INFO = 'video'

STREAM_HEADER_VIDEO = '<4sIQQIIHII'
STREAM_HEADER_AUDIO = '<4sIQQIIHHHI'

_print = mediainfo._debug

class OgmInfo(mediainfo.AVInfo):
    def __init__(self, file):
        mediainfo.AVInfo.__init__(self)
        self.lastgran = 0
        self.samplerate = 1
        while self._parseOGGS(file):
            pass
        _print("%d / %d" % (self.lastgran, self.samplerate))
        self.length = self.lastgran / self.samplerate
        
    def _parseOGGS(self,file):
        h = file.read(27)
        if len(h) < 27:
            return 0
        if h[:4] != "OggS":
            self.valid = 0
            return
        self.valid = 1
        version = ord(h[4])
        if version != 0:
            print("Unsupported OGG/OGM Version %d." % version)
            return
        head = struct.unpack('<BQIIIB', h[5:])
        headertype, granulepos, serial, pageseqno, checksum, pageSegCount = head
        self.valid = 1
        self.mime = 'application/ogm'
        self.type = 'OGG Media'
        tab = file.read(pageSegCount)
        self.lastgran = granulepos
        nextlen = 0
        for i in range(len(tab)):
            nextlen += ord(tab[i])
#        if nextlen > 10000:
            # Skip over large header
#            file.seek(nextlen,1)
        else:
            h = file.read(nextlen)
            packettype = ord(h[0]) & PACKET_TYPE_BITS 
            if packettype == PACKET_TYPE_HEADER:
                self._parseHeader(h, granulepos)
            elif packettype == PACKED_TYPE_METADATA:
                self._parseMeta(h)
        return 1
        
    def _parseMeta(self,h):
        flags = ord(h[0])
        headerlen = len(h)
        if headerlen >= 7 and h[1:7] == 'vorbis':
            header = {}
            nextlen, self.encoder = self._extractHeaderString(h[7:])
            numItems = struct.unpack('<I',h[7+nextlen:7+nextlen+4])[0]
            start = 7+4+nextlen
            for i in range(numItems):
                (nextlen, s) = self._extractHeaderString(h[start:])
                start += nextlen
                a = re.split('=',s)
                header[(a[0]).upper()]=a[1]
                print a
            # Put Header fields into info fields
            if header.has_key('TITLE'):
                self.title = header['TITLE']
            if header.has_key('ALBUM'):
                self.album = header['ALBUM']
            if header.has_key('ARTIST'):
                self.artist = header['ARTIST']            
            if header.has_key('COMMENT'):
                self.comment = header['COMMENT']
            if header.has_key('DATE'):
                self.date = header['DATE']
            if header.has_key('ENCODER'):
                self.encoder = header['ENCODER']
            if header.has_key('TRACKNUMBER'):
                self.trackno = header['TRACKNUMBER']
            if header.has_key('LANGUAGE'):
                self.language = header['LANGUAGE']            
            self.type = 'OGG Vorbis'
            self.subtype = ''
            self.appendtable('VORBISCOMMENT', header)
            pass


    def _parseHeader(self,header,granule):
        headerlen = len(header)
        flags = ord(header[0])
        if headerlen >= 30 and header[1:7] == 'vorbis':
            print("Vorbis Audio Header")
            ai = mediainfo.AudioInfo()
            ai.version, ai.channels, ai.samplerate, bitrate_max, ai.bitrate, bitrate_min, blocksize, framing = struct.unpack('<IBIiiiBB',header[7:7+23])
            ai.codec = 'Vorbis'
            self.audio.append(ai)
            #self.samplerate = ai.samplerate
            pass
        elif headerlen >= 7 and header[1:7] == 'theora':            
            # Theora Header
            # XXX Finish Me
            vi = mediainfo.VideoInfo()
            vi.codec = 'theora'
            self.video.append(vi)
            pass
        elif headerlen >= 142 and header[1:36] == 'Direct Show Samples embedded in Ogg':
            # Old Directshow format
            # XXX Finish Me
            vi = mediainfo.VideoInfo()
            vi.codec = 'dshow'
            self.video.append(vi)            
            pass
        elif flags & PACKET_TYPE_BITS == PACKET_TYPE_HEADER and headerlen >= struct.calcsize(STREAM_HEADER_VIDEO)+1:
            # New Directshow Format
            htype = header[1:9]
            if htype[:5] == 'video':
                streamheader = struct.unpack( STREAM_HEADER_VIDEO, header[9:struct.calcsize(STREAM_HEADER_VIDEO)+9] )
                vi = mediainfo.VideoInfo()
                (type, ssize, timeunit, vi.samplerate, vi.length, buffersize, vi.bitrate, vi.width, vi.height) = streamheader
                vi.width /= 65536
                vi.height /= 65536
                # XXX samplerate, length, bitrate are very wrong
                try:
                    vi.codec = fourcc.RIFFCODEC[type]
                except:
                    vi.codec = 'Unknown (%s)' % type
                vi.fps = 10000000 / timeunit
                self.samplerate = vi.samplerate
                self.video.append(vi)
            elif htype[:5] == 'audio':
                streamheader = struct.unpack( STREAM_HEADER_AUDIO, header[9:struct.calcsize(STREAM_HEADER_AUDIO)+9] )
                ai = mediainfo.AudioInfo()
                (type, ssize, timeunit, ai.samplerate, ai.length, buffersize, ai.bitrate, ai.channels, bloc, ai.bitrate) = streamheader
                self.samplerate = ai.samplerate
                print "Samplerate %d" % self.samplerate
                self.audio.append(ai)

    def _extractHeaderString(self,header):
        len = struct.unpack( '<I', header[:4] )[0]
        return (len+4,header[4:4+len])



mmpython.registertype( 'application/ogm', ('ogm',), mediainfo.TYPE_AV, OgmInfo )
