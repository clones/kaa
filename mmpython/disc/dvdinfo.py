import ifoparser
import mediainfo


class DVDAudio(mediainfo.AudioInfo):
    def __init__(self, title, number):
        self.number = number
        self.title  = title
        self.id, self.language, self.codec, self.channels, self.samplerate = \
                 ifoparser.audio(title, number)


class DVDTitle(mediainfo.AVInfo):
    def __init__(self, number):
        mediainfo.AVInfo.__init__(self)
        self.number = number
        self.chapters, self.angles, self.length, audio_num, \
                       subtitles_num = ifoparser.title(number)

        self.mime = 'video/mpeg'
        for a in range(1, audio_num+1):
            self.audio.append(DVDAudio(number, a))
            
        for s in range(1, subtitles_num+1):
            self.subtitles.append(ifoparser.subtitle(number, s)[0])


class DVDInfo(mediainfo.DiscInfo):
    def __init__(self,device):
        mediainfo.DiscInfo.__init__(self)
        self.context = 'video'
        self.offset = 0
        self.valid = self.isDisc(device)
        self.mime = 'video/dvd'
        self.type = 'dvd video'

        self.keys.append('title_list')
        

    def isDisc(self, device):
        if mediainfo.DiscInfo.isDisc(self, device) != 2:
            return 0

        # brute force reading of the device to find out if it is a DVD
        f = open(device,'rb')
        f.seek(32808, 0)
        buffer = f.read(50000)

        if buffer.find('UDF') == -1:
            f.close()
            return 0

        # seems to be a DVD, read a little bit more
        buffer += f.read(550000)
        f.close()

        if buffer.find('VIDEO_TS') == -1 and buffer.find('VIDEO_TS.IFO') == -1 and \
               buffer.find('OSTA UDF Compliant') == -1:
            return 0

        # OK, try libdvdread
        title_num = ifoparser.open(device)

        if not title_num:
            return 0

        self.title_list = []
        for title in range(1, title_num+1):
            self.title_list.append(DVDTitle(title))

        ifoparser.close()
        return 1



factory = mediainfo.get_singleton()  
dvdinfo = DVDInfo
factory.register( 'video/dvd', mediainfo.DEVICE, mediainfo.TYPE_AV, dvdinfo )
print "dvd video type registered"
