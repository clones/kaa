
import sndhdr
import mediainfo

class PCMInfo(mediainfo.AudioInfo):
    def _what(self,f):
        """Recognize sound headers"""
        h = f.read(512)
        for tf in sndhdr.tests:
            res = tf(h, f)
            if res:
                return res
        return None

    def __init__(self,file):
       mediainfo.AudioInfo.__init__(self)
       t = self._what(file)
       if t:
           (self.type, self.samplerate, self.channels, self.bitrate, self.samplebits) = t
           self.mime = "audio/%s" % self.type
           self.valid = 1
       else:
           self.valid = 0
           return
       

factory = mediainfo.get_singleton()
pcminfo = PCMInfo
factory.register( 'application/pcm', ['wav','aif','voc','au'], mediainfo.TYPE_AUDIO, pcminfo )
print "pcm types registered"