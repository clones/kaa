#
#
#


from mmpython import mediainfo
import struct

VORBIS_PACKET_INFO = '\01vorbis'
VORBIS_PACKET_HEADER = '\03vorbis'
VORBIS_PACKET_SETUP = '\05vorbis'
VORBIS_VIDEO_PACKET_INFO = '\01video'

_print = mediainfo._debug

class OgmInfo(mediainfo.AVInfo):
    def __init__(self, file, filename):
        mediainfo.AVInfo.__init__(self)
        h = file.read(27)
        if h[:5] != "OggS\00":
            self.valid = 0
            return
        if ord(h[5]) != 2:
            print("Invalid header type flag (trying to go ahead anyway)")
        self.pageSegCount = ord(h[-1])
        self.valid = 1
        self.mime = 'application/ogm'
        self.type = 'OGG Media'
        # Skip the PageSegCount
        file.seek(self.pageSegCount,1)
        h = file.read(9+8)
        if h[:6] != VORBIS_VIDEO_PACKET_INFO:
            print("Wrong vorbis header type, giving up.")
            self.valid = 0
            return
        return
        
        # This stuff is unstable:        
        vcodec, dlen = struct.unpack('<9x4sI', h[:17])
        crap = file.read(dlen-8-8)
        #info = file.read(23)
        #self.version, self.channels, self.samplerate, bitrate_max, self.bitrate, bitrate_min, blocksize, framing = struct.unpack('<IBIiiiBB',info[:23])
        # INFO Header, read Oggs and skip 10 bytes
        h = file.read(27)        
        if h[:4] == 'OggS':
            (serial, pagesequence, checksum, numEntries) = struct.unpack( '<14xIIIB', h )
            # skip past numEntries
            file.seek(numEntries,1)
            h = file.read(7)
            if h != VORBIS_PACKET_HEADER:
                print("Not a corrent info header")
                return
        else:
            print h[:4]

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
factory.register( 'application/ogm', ('ogm',), mediainfo.TYPE_AV, OgmInfo )
