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
        self.junkStart = None
        self.infoStart = None
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
        key = t[i:i+4]
        sz = struct.unpack('<I',t[i+4:i+8])[0]
        i+=8
        value = t[i:]
        if key == 'strh':
            retval[key] = self.parseSTRH(value)
            i += sz
        else:
            print "Error"
        key = t[i:i+4]
        sz = struct.unpack('<I',t[i+4:i+8])[0]
        i+=8
        value = t[i:]
        if key == 'strf':
            retval[key] = self.parseSTRF(value,retval['strh']['fccType'])
            i += sz
        else:
            print "parseSTRL: Unknown Key %s" % key        
        return ( retval, i )
            
    def parseLIST(self,t):
        retval = {}
        i = 0
        size = len(t)
        print "parseList of size %d" % size
        while i < size:
            # skip zero
            while ord(t[i]) == 0: i += 1
            key = t[i:i+4]
            sz = 0
            print "parseList %s" % key
            if key == 'LIST':
                print "->"
                sz = struct.unpack('<I',t[i+4:i+8])[0]
                print "SUBLIST: len: %d, %d" % ( sz, i+4 )
                i+=8
                key = "LIST:"+t[i:i+4]
                value = self.parseLIST(t[i:i+sz])
                print "<-"
                if key == 'strl':
                    for k in value.keys():
                        retval[k] = value[k]
                else:
                    retval[key] = value
                i+=sz
            elif key == 'avih':
                print "SUBAVIH"
                sz = struct.unpack('<I',t[i+4:i+8])[0]
                i += 8
                value = self.parseAVIH(t[i:i+sz])
                i += sz
                retval[key] = value
            elif key == 'strl':
                i += 4
                (value, sz) = self.parseSTRL(t[i:])
                print "SUBSTRL: len: %d" % sz
                key = value['strh']['fccType']
                i += sz
                retval[key] = value
            else:
                sz = struct.unpack('<I',t[i+4:i+8])[0]
                # print "Unknown Key: %s, len: %d" % (key,sz)
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
                self.info = value
            elif key == 'MID ':
                self.mid = value
        elif name == 'JUNK':
            self.junkStart = file.tell() - 8
            self.junkSize = size
        else:        
            t = file.seek(size,1)
#            print "Skipping %s" % name
        return 0

    def buildTag(self,key,value):
        l = len(value)
        return struct.pack('<4sI%ds'%l, key[:4], l, value[:l])


    def setInfo(self,file,hash):
        if self.junkStart == None:
            raise "junkstart missing"
        tags = []
        size = 4 # Length of 'INFO'
        # Build String List and compute req. size
        for key in hash.keys():
            tag = self.buildTag( key, hash[key] )
            tags.append(tag)
            size += len(tag)
            print tag
        if self.infoStart != None:
            print "Infostart found. %i" % (self.infoStart)
            # Read current info size
            file.seek(self.infoStart,0)
            s = file.read(12)
            (list, info, size) = struct.unpack('<4s4sI',s)
            self.junkSize += size + 8
        else:
            self.infoStart = self.junkStart
            print "Infostart computed. %i" % (self.infoStart)
        file.seek(self.infoStart,0)
        if ( size > self.junkSize - 8 ):
            raise "Too large"
        file.write( "LIST" + struct.pack('<I',size) + "INFO" )
        for tag in tags:
            file.write( tag )
        print "Junksize %i" % (self.junkSize-size-8)
        file.write( "JUNK" + struct.pack('<I',self.junkSize-size-8) )
        

factory = mediainfo.get_singleton()
aviinfo = RiffInfo
factory.register( 'video/avi', ['avi'], mediainfo.TYPE_VIDEO, aviinfo )
print "riff type registered"

if __name__ == '__main__':
    import sys
    f = open(sys.argv[1], 'rb')
    o = RiffInfo(f)
    f.close()
    f = open(sys.argv[1], 'rb+')
    o.setInfo(f, { 'INAM':'Hans Inam Test', 'IPOK': 'Ipok Test2' } )
    f.close()
