import mediainfo
import cdrom

class VCDInfo(mediainfo.DiscInfo):
    def __init__(self,device):
        mediainfo.DiscInfo.__init__(self)
        self.context = 'video'
        self.offset = 0
        self.valid = self.isDisc(device)
        self.mime = 'video/vcd'
        self.type = 'vcd video'        

    def isDisc(self, device):
        if mediainfo.DiscInfo.isDisc(self, device) != 2:
            return 0
        
        # brute force reading of the device to find out if it is a VCD
        f = open(device,'rb')
        f.seek(32808, 0)
        buffer = f.read(50000)
        f.close()

        if buffer.find('SVCD') > 0 and buffer.find('TRACKS.SVD') > 0 and \
               buffer.find('ENTRIES.SVD') > 0:
            print 'This is a SVCD'

        elif buffer.find('INFO.VCD') > 0 and buffer.find('ENTRIES.VCD') > 0:
            print 'This is a VCD'

        else:
            return None

        # read the tracks to generate the title list
        device = open(device)
        (first, last) = cdrom.toc_header(device)

        lmin = 0
        lsec = 0

        num = 0
        for i in range(first, last + 2):
            if i == last + 1:
                min, sec, frames = cdrom.leadout(device)
            else:
                min, sec, frames = cdrom.toc_entry(device, i)
            if num:
                self.tracks.append(min-lmin)
            num += 1
            lmin, lsec = min, sec
        device.close()
        return 1

    
factory = mediainfo.get_singleton()  
vcdinfo = VCDInfo
factory.register( 'video/vcd', mediainfo.DEVICE, mediainfo.TYPE_AV, vcdinfo )
print "vcd video type registered"
