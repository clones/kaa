#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.8  2003/06/08 13:11:25  dischi
# removed print at the end and moved it into register
#
# Revision 1.7  2003/06/07 23:32:11  the_krow
# changed names to new format
# debug messages
#
# Revision 1.6  2003/05/13 15:23:59  the_krow
# IPTC
#
# Revision 1.5  2003/05/13 12:31:43  the_krow
# + Copyright Notice
#
# -----------------------------------------------------------------------
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

VORBIS_PACKET_INFO = '\01vorbis'
VORBIS_PACKET_HEADER = '\03vorbis'
VORBIS_PACKET_SETUP = '\05vorbis'

_print = mediainfo._debug

class OggInfo(mediainfo.AudioInfo):
    def __init__(self,file):
        mediainfo.AudioInfo.__init__(self)
        h = file.read(4+1+1+20+1)
        if h[:5] != "OggS\00":
            _print("Invalid header")
            self.valid = 0
            return
        if ord(h[5]) != 2:
            _print("Invalid header type flag (trying to go ahead anyway)")
        self.pageSegCount = ord(h[-1])
        # Skip the PageSegCount
        file.seek(self.pageSegCount,1)
        h = file.read(7)
        if h != VORBIS_PACKET_INFO:
            _print("Wrong vorbis header type, giving up.")
            self.valid = 0
            return
        self.valid = 1
        self.mime = 'application/ogg'
        self.header = {}
        info = file.read(23)
        self.version, self.channels, self.samplerate, bitrate_max, self.bitrate, bitrate_min, blocksize, framing = struct.unpack('<IBIiiiBB',info[:23])
        # INFO Header, read Oggs and skip 10 bytes
        h = file.read(4+10+13)        
        if h[:4] == 'OggS':
            (serial, pagesequence, checksum, numEntries) = struct.unpack( '<14xIIIB', h )
            # skip past numEntries
            file.seek(numEntries,1)
            h = file.read(7)
            if h != VORBIS_PACKET_HEADER:
                # Not a corrent info header
                return                        
            self.header['vendor'] = self._extractHeaderString(file)
            numItems = struct.unpack('<I',file.read(4))[0]
            for i in range(numItems):
                s = self._extractHeaderString(file)
                a = re.split('=',s)
                self.header[a[0]]=a[1]
            # Put Header fields into info fields
            if self.header.has_key('TITLE'):
                self.title = self.header['TITLE']
            if self.header.has_key('ALBUM'):
                self.album = self.header['ALBUM']
            if self.header.has_key('ARTIST'):
                self.artist = self.header['ARTIST']            
            if self.header.has_key('COMMENT'):
                self.comment = self.header['COMMENT']
            if self.header.has_key('DATE'):
                self.date = self.header['DATE']
            if self.header.has_key('vendor'):
                self.encoder = self.header['vendor']
            self.type = 'OGG Vorbis'
            self.subtype = ''
            self.length = self._calculateTrackLength(file)
            
    def __getitem__(self,key):
        i = self.info[key]
        if i: return i
        else: return self.header[key]
            
                    
    def _extractHeaderString(self,f):
        len = struct.unpack( '<I', f.read(4) )[0]
        return f.read(len)
    

    def _calculateTrackLength(self,f):
        # read the rest of the file into a buffer
        h = f.read()
        granule_position = 0
        # search for each 'OggS' in h        
        if len(h):
            idx = h.rfind('OggS')
            if idx < 0:
                return 0
            pageSize = 0
            h = h[idx+4:]
            (check, type, granule_position, absPos, serial, pageN, crc, segs) = struct.unpack( '<BBIIIIIB', h[:23] )            
            if check != 0:
                print h[:10]
                return
            _print("granule = %d / %d" % (granule_position, absPos))
        # the last one is the one we are interested in
        return (granule_position / self.samplerate)



factory = mediainfo.get_singleton()
factory.register( 'application/ogg', ['ogg'], mediainfo.TYPE_AUDIO, OggInfo )

if __name__ == '__main__':
    import sys
    o = OggInfo(open(sys.argv[1], 'rb'))
    print "INFO:"
    print o.info
    print "HEADER:"
    print o.header
