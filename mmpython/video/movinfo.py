import re
import struct
import mediainfo
import string
import fourcc


class MovInfo(mediainfo.VideoInfo):
    def __init__(self,file):
        mediainfo.VideoInfo.__init__(self)
        self.context = 'video'
        self.valid = 0
        self.mime = 'video/quicktime'
        self.type = 'Quicktime Video'
        h = file.read(8)
        (type1,type2) = struct.unpack('<II',h)
        if ( type2 == 0x6d6f6f76 ) or ( type2 == 0x6d646174 ) or ( type2 == 0x706e6f74 ):
            self.valid = 1


factory = mediainfo.get_singleton()  
movinfo = MovInfo
factory.register( 'video/quicktime', ['mov', 'qt'], mediainfo.TYPE_VIDEO, movinfo )
print "Quicktime video type registered"
