import re
import struct
import mediainfo

VORBIS_PACKET_INFO = '\01vorbis'
VORBIS_PACKET_HEADER = '\03vorbis'
VORBIS_PACKET_SETUP = '\05vorbis'

class OggInfo(mediainfo.AudioInfo):
    def __init__(self,file):
        mediainfo.AudioInfo.__init__(self)
        h = file.read(4096)
        if h[:4] != "OggS":
            self.valid = 0
            return
        self.valid = 1
        self.mime = 'application/ogg'
        self.header = {}
        idx = h.find(VORBIS_PACKET_INFO)
        if idx == -1:
            self.valid = 0
            return
        info = h[idx+len(VORBIS_PACKET_INFO):]
        junk, self.channels, self.samplerate, bitmax, self.audiobitrate, bitmin = struct.unpack('<IBIiii',info[:21])
        idx = h.find(VORBIS_PACKET_HEADER)
        if idx != -1:
            header = h[idx+len(VORBIS_PACKET_HEADER):]
            self.header['vendor'] = self._extractHeaderString(header,0)
            startoffset = struct.unpack('<I',header[:4])[0] + 8
            for i in range(struct.unpack('<I',header[startoffset-4:startoffset])[0]):
                s = self._extractHeaderString(header,startoffset)
                a = re.split('=',s)
                self.header[a[0]]=a[1]
                startoffset += struct.unpack('<I',header[startoffset:startoffset+4])[0] + 4
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
            
    def __getitem__(self,key):
        i = self.info[key]
        if i: return i
        else: return self.header[key]
            
                    
    def _extractHeaderString(self,h,offset):
        return h[offset+4:offset+4+struct.unpack('<I',h[offset:offset+4])[0]]


factory = mediainfo.get_singleton()
ogginfo = OggInfo
factory.register( 'application/ogg', ['ogg'], mediainfo.TYPE_AUDIO, ogginfo )
print "ogg type registered"

if __name__ == '__main__':
    import sys
    o = OggInfo(open(sys.argv[1], 'rb'))
    print "INFO:"
    print o.info
    print "HEADER:"
    print o.header
