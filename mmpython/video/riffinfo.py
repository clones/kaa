import re
import struct
import mediainfo
import string
import fourcc

# List of tags
# http://kibus1.narod.ru/frames_eng.htm?sof/abcavi/infotags.htm
# File Format
# http://www.taenam.co.kr/pds/documents/odmlff2.pdf

class RiffInfo(mediainfo.VideoInfo):
    def __init__(self,file):
        mediainfo.VideoInfo.__init__(self)
        # read the header
        h = file.read(12)
        if h[:4] != "RIFF" and h[:4] != 'SDSS':
            self.valid = 0
            return
        self.valid = 1
        self.mime = 'application/x-wave'
        self.info = {}
        self.header = {}
        self.type = h[8:12]
        if self.type == 'AVI ':
            self.mime = 'video/avi'
        elif self.type == 'WAVE':
            self.mime = 'application/x-wave'
        while not self.parseRIFFChunk(file):
            pass
        # Push the result into funky attributes of self
        self.setitem('title',self.info,'INAM')
        self.setitem('artist',self.info,'IART')
        self.setitem('product',self.info,'IPRD')
        self.setitem('date',self.info,'ICRD')
        self.setitem('comment',self.info,'ICMT')
        self.setitem('language',self.info,'ILNG')
        self.setitem('keywords',self.info,'IKEY')
        self.setitem('trackno',self.info,'IPRT')
        self.setitem('trackof',self.info,'IFRM')
        self.setitem('producer',self.info,'IPRO')
        self.setitem('writer',self.info,'IWRI')
        self.setitem('genre',self.info,'IGNR')
        # TODO ... add all this: 
        #    http://kibus1.narod.ru/frames_eng.htm?sof/abcavi/infotags.htm
        
        
    def _extractHeaderString(self,h,offset):
        return h[offset+4:offset+4+struct.unpack('<I',h[offset:offset+4])[0]]

    def parseAVIH(self,t):
        retval = {}
        retval['dwMicroSecPerFrame'] = struct.unpack('<I',t[:4])[0]
        v = struct.unpack('<IIIIIIIIIIIIII',t[4:60])
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
            print "ERROR: Corrupt AVI"
            self.valid = 0
            return {}

        return retval
        
    def parseSTRH(self,t):
        retval = {}
        retval['fccType'] = t[0:4]
        #print "%s : %d bytes" % ( retval['fccType'], len(t) )
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
        return retval      

    def parseSTRF(self,t,fccType):
        retval = {}
        if fccType == 'auds':
            ( retval['wFormatTag'],
              retval['nChannels'],
              retval['nSamplesPerSec'],
              retval['nAvgBytesPerSec'],
              retval['nBlockAlign'],
              retval['nBitsPerSample'],
            ) = struct.unpack('<HHHHHH',t[0:12])  
            self.samplerate = retval['nSamplesPerSec']
            self.audiochannels = retval['nChannels']
            self.samplebits = retval['nBitsPerSample']
            self.audiocodec = fourcc.RIFFWAVE[retval['wFormatTag']]
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
            self.height = retval['biHeight']
            self.width = retval['biWidth']
            self.videocodec = fourcc.RIFFCODEC[t[16:20]]
        return retval
        
    def parseSTRL(self,t):
        retval = {}
        size = len(t)
        i = 0
        while i < size-8:
            key = t[i:i+4]
            sz = struct.unpack('<I',t[i+4:i+8])[0]
            value = t[i+8:i+sz+8]
            if key == 'strh':
                retval[key] = self.parseSTRH(value)
            elif key == 'strf':
                retval[key] = self.parseSTRF(value,retval['strh']['fccType'])
            else:
                #print "parseSTRL: Unknown Key %s" % key
                retval[key] = value
            i += 8+sz
        
        return retval
            

    def parseLIST(self,t):
        # check INFO tags but skip long ones
        retval = {}
        i = 0
        size = len(t)
        while i < size:
            # skip zero
            while ord(t[i]) == 0: i += 1
            key = t[i:i+4]
            sz = struct.unpack('<I',t[i+4:i+8])[0]
            # print "parseList %s" % key
            if key == 'LIST':
                key = t[i+8:i+12]
                #print "parseList %s" % key
                value = self.parseLIST(t[i+8:i+12+sz])
                if key == 'strl':
                    for k in value.keys():
                        retval[k] = value[k]
                else:
                    retval[key] = value
            elif key == 'avih':
                value = self.parseAVIH(t[i+4:i+8+sz])
                retval[key] = value
            elif key == 'strl':
                value = self.parseSTRL(t[i+4:i+8+sz])
                key = value['strh']['fccType']
                # print "adding %s" % (key)
                retval[key] = value
            else:
                value = self._extractHeaderString(t,i+4)
                retval[key] = value
            i += sz + 8
        return retval
        

    def parseRIFFChunk(self,file):
        h = file.read(8)
        if len(h) < 4: return 1
        name = h[:4]
        size = struct.unpack('<I',h[4:8])[0]        
        if name == 'LIST' and size < 13000:
            t = file.read(size)
            key = t[:4]
            value = self.parseLIST(t[4:])
            self.header[key] = value
            if key == 'INFO':
                self.info = value
            elif key == 'MID ':
                self.mid = value
        else:
            t = file.seek(size,1)
            #print "Ignoring %s" % name
        return 0
        

factory = mediainfo.get_singleton()
aviinfo = RiffInfo
factory.register( 'video/avi', ['avi'], mediainfo.TYPE_VIDEO, aviinfo )
print "riff type registered"

if __name__ == '__main__':
    import sys
    o = RiffInfo(open(sys.argv[1], 'rb'))
    print "INFO:"
    print o.info
    print "MID:"
    print o.mid
    print "HEADER:"
    print o.header
    print "WIDTH: %d" % o.width
    print "HEIGT: %d" % o.height
