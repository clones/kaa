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




class MpegInfo(mediainfo.VideoInfo):
    def __init__(self,file):
        mediainfo.VideoInfo.__init__(self)
        self.context = 'video'
        self.valid = self.isVideo(file)
        self.mime = 'video/mpeg'
        self.type = 'mpeg video'

    def isVideo(self,file):
        buffer = file.read(1000)
        offset = 0
        while ( offset <= len(buffer) - 4 ):
            a = ord(buffer[offset])
            offset+=1
            if a != 0:
                continue
            b = ord(buffer[offset])
            if b != 0:
                continue
            c = ord(buffer[offset+1])
            if c != 1:
                continue
            d = ord(buffer[offset+2])
            if ( d == SEQ_START_CODE ):
                print "right seq start code"
	        return 1
	    elif ( self.context == 'video' ) and ( d == SYS_PKT ):
	        print "SC: 0x%x Returning because video context\n" % d 
	        return 0
        return 1


factory = mediainfo.get_singleton()  
mpginfo = MpegInfo
factory.register( 'video/mpeg', ['mpeg','mpg','mp4'], mediainfo.TYPE_VIDEO, mpginfo )
print "mpeg video type registered"
