#if 0
# $Id$
# $Log$
# Revision 1.15  2003/06/20 14:43:57  the_krow
# Putting Metadata into MediaInfo from AVIInfo Table
#
# Revision 1.14  2003/06/09 16:10:52  dischi
# error handling
#
# Revision 1.13  2003/06/08 19:53:21  dischi
# also give the filename to init for additional data tests
#
# Revision 1.12  2003/06/08 13:44:58  dischi
# Changed all imports to use the complete mmpython path for mediainfo
#
# Revision 1.11  2003/06/08 13:11:38  dischi
# removed print at the end and moved it into register
#
# Revision 1.10  2003/06/07 23:10:50  the_krow
# Changed mp3 into new format.
#
# Revision 1.9  2003/06/07 22:30:22  the_krow
# added new avinfo structure
#
# Revision 1.8  2003/06/07 21:48:47  the_krow
# Added Copying info
# started changing riffinfo to new AV stuff
#
# Revision 1.7  2003/05/13 12:31:43  the_krow
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

# List of tags
# http://kibus1.narod.ru/frames_eng.htm?sof/abcavi/infotags.htm
# File Format
# http://www.taenam.co.kr/pds/documents/odmlff2.pdf

_print = mediainfo._debug

class RiffInfo(mediainfo.AVInfo):
    def __init__(self,file,filename):
        mediainfo.AVInfo.__init__(self)
        # read the header
        h = file.read(12)
        if h[:4] != "RIFF" and h[:4] != 'SDSS':
            self.valid = 0
            return
        self.valid = 1
        self.mime = 'application/x-wave'
        
        self.header = {}
        self.junkStart = None
        self.infoStart = None
        self.type = h[8:12]
        if self.type == 'AVI ':
            self.mime = 'video/avi'
        elif self.type == 'WAVE':
            self.mime = 'application/x-wave'
        try:
            while not self.parseRIFFChunk(file):
                pass
        except IOError:
            if mediainfo.DEBUG: print 'error in file, stop parsing'
            pass
        
        info = None
        # Check if this has an AVIINFO table:        
        if self.tables.has_key('AVIINFO'):
            info = self.tables['AVIINFO']
        elif self.tables.has_key('AVIMID'):
            info = self.tables['AVIMID']
        # Push the result into funky attributes of self
        self.setitem('title', info,'INAM')
        self.setitem('artist', info,'IART')
        self.setitem('product', info,'IPRD')
        self.setitem('date', info,'ICRD')
        self.setitem('comment', info,'ICMT')
        self.setitem('language', info,'ILNG')
        self.setitem('keywords', info,'IKEY')
        self.setitem('trackno', info,'IPRT')
        self.setitem('trackof', info,'IFRM')
        self.setitem('producer', info,'IPRO')
        self.setitem('writer', info,'IWRI')
        self.setitem('genre', info,'IGNR')
        # TODO ... add all this: 
        #    http://kibus1.narod.ru/frames_eng.htm?sof/abcavi/infotags.htm
        
        
    def _extractHeaderString(self,h,offset,len):
        return h[offset:offset+len]

    def parseAVIH(self,t):
        retval = {}
        v = struct.unpack('<IIIIIIIIIIIIII',t[0:56])
        ( retval['dwMicroSecPerFrame'],
          retval['dwMaxBytesPerSec'],           
          retval['dwPaddingGranularity'], 
          retval['dwFlags'], 
          retval['dwTotalFrames'],
          retval['dwInitialFrames'],
          retval['dwStreams'],
          retval['dwSuggestedBufferSize'],
          retval['dwWidth'],
          retval['dwHeight'],
          retval['dwScale'],
          retval['dwRate'],
          retval['dwStart'],
          retval['dwLength'] ) = v
        if retval['dwMicroSecPerFrame'] == 0:
            _print("ERROR: Corrupt AVI")
            self.valid = 0
            return {}
        return retval
        
    def parseSTRH(self,t):
        retval = {}
        retval['fccType'] = t[0:4]
        _print("%s : %d bytes" % ( retval['fccType'], len(t)))
        if retval['fccType'] != 'auds':
            retval['fccHandler'] = t[4:8]
            v = struct.unpack('<IHHIIIIIIIII',t[8:52])
            ( retval['dwFlags'],
              retval['wPriority'],
              retval['wLanguage'],
              retval['dwInitialFrames'],
              retval['dwScale'],
              retval['dwRate'],
              retval['dwStart'],
              retval['dwLength'],
              retval['dwSuggestedBufferSize'],
              retval['dwQuality'],
              retval['dwSampleSize'],
              retval['rcFrame'], ) = v
            self.bitrate = retval['dwRate']
            self.length = retval['dwLength']
        # TODO: Add 'vids' parsing!!
        return retval

    def parseSTRF(self,t,strh):
        fccType = strh['fccType']
        retval = {}
        if fccType == 'auds':
            ( retval['wFormatTag'],
              retval['nChannels'],
              retval['nSamplesPerSec'],
              retval['nAvgBytesPerSec'],
              retval['nBlockAlign'],
              retval['nBitsPerSample'],
            ) = struct.unpack('<HHHHHH',t[0:12])
            ai = mediainfo.AudioInfo()
            ai.samplerate = retval['nSamplesPerSec']
            ai.channels = retval['nChannels']
            ai.samplebits = retval['nBitsPerSample']
            try:
                ai.codec = fourcc.RIFFWAVE[retval['wFormatTag']]
            except:
                ai.codec = "Unknown"            
            self.audio.append(ai)  
        elif fccType == 'vids':
            v = struct.unpack('<IIIHH',t[0:16])
            ( retval['biSize'],
              retval['biWidth'],
              retval['biHeight'],
              retval['biPlanes'],
              retval['biBitCount'], ) = v
            retval['fourcc'] = t[16:20]            
            v = struct.unpack('IIIII',t[20:40])
            ( retval['biSizeImage'],
              retval['biXPelsPerMeter'],
              retval['biYPelsPerMeter'],
              retval['biClrUsed'],
              retval['biClrImportant'], ) = v
            vi = mediainfo.VideoInfo()
            try:
                vi.codec = fourcc.RIFFCODEC[t[16:20]]
            except:
                vi.codec = "Unknown"
            vi.width = retval['biWidth']
            vi.height = retval['biHeight']            
            vi.length = strh['dwLength']
            self.video.append(vi)  
        return retval
        
    def parseSTRL(self,t):
        retval = {}
        size = len(t)
        i = 0
        key = t[i:i+4]
        sz = struct.unpack('<I',t[i+4:i+8])[0]
        i+=8
        value = t[i:]
        if key == 'strh':
            retval[key] = self.parseSTRH(value)
            i += sz
        else:
            _print("parseSTRL: Error")
#        if ord(t[i]) == 0: i = i+1
        key = t[i:i+4]
        sz = struct.unpack('<I',t[i+4:i+8])[0]
        i+=8
        value = t[i:]
        if key == 'strf':
            retval[key] = self.parseSTRF(value,retval['strh'])
            i += sz
        else:
            _print("parseSTRL: Unknown Key %s" % key)
        return ( retval, i )
            
    def parseLIST(self,t):
        retval = {}
        i = 0
        size = len(t)
        _print("parseList of size %d" % size)
        while i < size-8:
            # skip zero
            if ord(t[i]) == 0: i += 1
            key = t[i:i+4]
            sz = 0
            _print("parseList %s" % key)
            if key == 'LIST':
                _print("->")
                sz = struct.unpack('<I',t[i+4:i+8])[0]
                _print("SUBLIST: len: %d, %d" % ( sz, i+4 ))
                i+=8
                key = "LIST:"+t[i:i+4]
                value = self.parseLIST(t[i:i+sz])
                _print("<-")
                if key == 'strl':
                    for k in value.keys():
                        retval[k] = value[k]
                else:
                    retval[key] = value
                i+=sz
            elif key == 'avih':
                _print("SUBAVIH")
                sz = struct.unpack('<I',t[i+4:i+8])[0]
                i += 8
                value = self.parseAVIH(t[i:i+sz])
                i += sz
                retval[key] = value
            elif key == 'strl':
                i += 4
                (value, sz) = self.parseSTRL(t[i:])
                _print("SUBSTRL: len: %d" % sz)
                key = value['strh']['fccType']
                i += sz
                retval[key] = value
            else:
                sz = struct.unpack('<I',t[i+4:i+8])[0]
                _print("Unknown Key: %s, len: %d" % (key,sz))
                i+=8
                value = self._extractHeaderString(t,i,sz)
                retval[key] = value
                i+=sz
        return retval
        

    def parseRIFFChunk(self,file):
        h = file.read(8)
        if len(h) < 4: return 1
        name = h[:4]
        size = struct.unpack('<I',h[4:8])[0]        
        if name == 'LIST' and size < 10000:
            pos = file.tell() - 8
            t = file.read(size)
            key = t[:4]
            value = self.parseLIST(t[4:])
            self.header[key] = value
            if key == 'INFO':
                self.infoStart = pos
                self.appendtable( 'AVIINFO', value )
            elif key == 'MID ':
                self.appendtable( 'AVIMID', value )
        elif name == 'JUNK':
                self.junkStart = file.tell() - 8
                self.junkSize = size
        else:
            t = file.seek(size,1)
            _print("Skipping %s [%i]" % (name,size))
        return 0

    def buildTag(self,key,value):
        text = value + '\0'
        l = len(text)
        return struct.pack('<4sI%ds'%l, key[:4], l, text[:l])


    def setInfo(self,file,hash):
        if self.junkStart == None:
            raise "junkstart missing"
        tags = []
        size = 4 # Length of 'INFO'
        # Build String List and compute req. size
        for key in hash.keys():
            tag = self.buildTag( key, hash[key] )
            if (len(tag))%2 == 1: tag += '\0'
            tags.append(tag)
            size += len(tag)
            _print("Tag [%i]: %s" % (len(tag),tag))
        if self.infoStart != None:
            _print("Infostart found. %i" % (self.infoStart))
            # Read current info size
            file.seek(self.infoStart,0)
            s = file.read(12)
            (list, oldsize, info) = struct.unpack('<4sI4s',s)
            self.junkSize += oldsize + 8
        else:
            self.infoStart = self.junkStart
            _print("Infostart computed. %i" % (self.infoStart))
        file.seek(self.infoStart,0)
        if ( size > self.junkSize - 8 ):
            raise "Too large"
        file.write( "LIST" + struct.pack('<I',size) + "INFO" )
        for tag in tags:
            file.write( tag )
        _print("Junksize %i" % (self.junkSize-size-8))
        file.write( "JUNK" + struct.pack('<I',self.junkSize-size-8) )
        

factory = mediainfo.get_singleton()
factory.register( 'video/avi', ('avi',), mediainfo.TYPE_AV, RiffInfo )


if __name__ == '__main__':
    import sys
    f = open(sys.argv[1], 'rb')
    o = RiffInfo(f)
    f.close()
    f = open(sys.argv[1], 'rb+')
    o.setInfo(f, { 'INAM':'Hans Inam Test', 'IWRI': 'My Writer' } )
    f.close()
