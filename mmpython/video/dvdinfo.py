import ifoinfo
import mediainfo



class DVDAudio:
    def __init__(self, title, number):
        self.number = number
        self.title  = title
        self.id, self.lang, self.format, self.channels, self.freq = \
                 ifoinfo.audio(title, number)


class DVDTitle:
    def __init__(self, number):
        self.number = number
        self.chapters, self.angles, self.playback_time, audio_num, \
                       subtitles_num = ifoinfo.title(number)

        self.audio = []
        for a in range(1, audio_num+1):
            self.audio.append(DVDAudio(number, a))
            
        self.subtitles = []
        for s in range(1, subtitles_num+1):
            self.subtitles.append(ifoinfo.subtitle(number, s)[0])



class DVDInfo(mediainfo.VideoInfo):
    def __init__(self,device):
        mediainfo.VideoInfo.__init__(self)
        self.context = 'video'
        self.offset = 0
        self.valid = self.isVideo(device)
        self.mime = 'video/dvd'
        self.type = 'dvd video'

        self.keys.append('title_list')
        
    def isVideo(self, device):
        title_num = ifoinfo.open(device)

        if not title_num:
            return 0

        self.title_list = []
        for title in range(1, title_num+1):
            self.title_list.append(DVDTitle(title))

        ifoinfo.close()
        return 1

factory = mediainfo.get_singleton()  
dvdinfo = DVDInfo
factory.register( 'video/dvd', mediainfo.DEVICE, mediainfo.TYPE_VIDEO, dvdinfo )
print "dvd video type registered"
