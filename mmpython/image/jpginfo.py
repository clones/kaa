import mediainfo
import IPTC
import EXIF
import Image

# interesting file format info:
# http://www.dcs.ed.ac.uk/home/mxr/gfx/2d-hi.html


class JPGInfo(mediainfo.ImageInfo):

    def __init__(self,file):
        mediainfo.ImageInfo.__init__(self)
        self.iptc = None
        try:
            im = Image.open(file)
            self.valid = 1
        except:
            self.valid = 0
            return
        
        self.mime = 'image/jpeg'
        self.type = 'jpeg image'
        self.iptc = IPTC.getiptcinfo(im)
        file.seek(0)
        self.exif = EXIF.process_file(file)
        if self.exif:
            self.setitem( 'comment', self.exif, 'EXIF UserComment' )
            self.setitem( 'width', self.exif, 'EXIF ExifImageWidth'  )
            self.setitem( 'height', self.exif, 'EXIF ExifImageHeight' )
            self.setitem( 'date', self.exif, 'Image DateTime' )            
            self.setitem( 'artist', self.exif, 'Image Artist' )
            self.setitem( 'hardware', self.exif, 'Image Model' )
            self.setitem( 'software', self.exif, 'Image Software' )
            self.setitem( 'thumbnail', self.exif, 'JPEGThumbnail' ) 
        if self.iptc:
            self.setitem( 'title', self.iptc, (2,5) ) 
            self.setitem( 'date' , self.iptc, (2,55) )
            self.setitem( 'comment', self.iptc, (2,105) )
            self.setitem( 'keywords', self.iptc, (2,25) )
            self.setitem( 'artist', self.iptc, (2,80) )
            self.setitem( 'country', self.iptc, (2,100) ) 
        self.height = self.exif.keys()
        return
       

factory = mediainfo.get_singleton()
jpginfo = JPGInfo
factory.register( 'image/jpeg', ['jpg','jpeg'], mediainfo.TYPE_IMAGE, jpginfo )
print "jpeg type registered"