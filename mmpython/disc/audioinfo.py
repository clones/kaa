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
        print "Getting disc id in CDDB format...",

        disc_id = DiscID.disc_id(cdrom)
        
        print "Disc ID: %08lx Num tracks: %d" % (disc_id[0], disc_id[1])
        print "Querying CDDB for info on disc...",
        
        (query_stat, query_info) = CDDB.query(disc_id)

        if query_stat == 200:
            print ("success!\nQuerying CDDB for track info of `%s'... " % 
                   query_info['title']),

            (read_stat, read_info) = CDDB.read(query_info['category'], 
                                               query_info['disc_id'])
            if read_stat == 210:
                print "success!"
                    # Start from 0, not 1
                    # thanks to bgp for the fix!
                for i in range(0, disc_id[1]):
                    print "Track %.02d: %s" % (i+1, read_info['TTITLE' + `i`])
            else:
                print "failure getting track info, status: %i" % read_stat

        elif query_stat == 210 or query_stat == 211:
            print "multiple matches found! Matches are:"
            for i in query_info:
                print "ID: %s Category: %s Title: %s" % \
                      (i['disc_id'], i['category'], i['title'])

        else:
            print "failure getting disc info, status %i" % query_stat
        return 1
    
        
factory = mediainfo.get_singleton()  
audioinfo = AudioInfo
factory.register( 'sudio/cd', mediainfo.DEVICE, mediainfo.TYPE_AUDIO, audioinfo )
print "audio cd type registered"
