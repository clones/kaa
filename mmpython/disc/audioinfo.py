import mediainfo
import DiscID
import CDDB

class AudioInfo(mediainfo.DiscInfo):
    def __init__(self,device):
        mediainfo.DiscInfo.__init__(self)
        self.context = 'audio'
        self.offset = 0
        self.valid = self.isDisc(device)
        self.mime = 'audio/cd'
        self.type = 'audio cd'
        

    def isDisc(self, device):
        if mediainfo.DiscInfo.isDisc(self, device) != 1:
            return 0
        
        cdrom = DiscID.open(device)
        disc_id = DiscID.disc_id(cdrom)
        
        (query_stat, query_info) = CDDB.query(disc_id)

        if query_stat == 210 or query_stat == 211:
            for i in query_info:
                if i['title'] != i['title'].upper():
                    query_info = i
                    break
            else:
                query_info = query_info[0]
            
        elif query_stat != 200:
            print "failure getting disc info, status %i" % query_stat
            return 1

        (read_stat, read_info) = CDDB.read(query_info['category'], 
                                           query_info['disc_id'])
        for key in query_info:
            setattr(self, key, query_info[key])
            if not key in self.keys:
                self.keys.append(key)

        if read_stat == 210:
            self.tracks = []
            self.keys.append('tracks')
            for i in range(0, disc_id[1]):
                self.tracks.append(read_info['TTITLE' + `i`])
        else:
            print "failure getting track info, status: %i" % read_stat

        return 1
    
        
factory = mediainfo.get_singleton()  
audioinfo = AudioInfo
factory.register( 'sudio/cd', mediainfo.DEVICE, mediainfo.TYPE_AUDIO, audioinfo )
print "audio cd type registered"
