import re
import struct
import mediainfo
import string
import fourcc


class AsfInfo(mediainfo.VideoInfo):
    def __init__(self,file):
        mediainfo.VideoInfo.__init__(self)
        self.context = 'video'
        self.valid = 0
        self.mime = 'video/asf'
        self.type = 'asf video'
        h = file.read(8)
        (type1,type2) = struct.unpack('<II',h)
        if ( type1 == 0x3026b275 ) or ( type1 == 0x75b22630 ):
            self.valid = 1


factory = mediainfo.get_singleton()  
asfinfo = AsfInfo
factory.register( 'video/asf', ['asf'], mediainfo.TYPE_VIDEO, asfinfo )
print "asf video type registered"
