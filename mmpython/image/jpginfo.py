#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.8  2003/05/13 18:28:17  the_krow
# JPEG Resolution
#
# Revision 1.7  2003/05/13 17:49:41  the_krow
# IPTC restructured\nEXIF Height read correctly\nJPEG Endmarker read
#
# Revision 1.6  2003/05/13 15:52:42  the_krow
# Caption added
#
# Revision 1.5  2003/05/13 15:23:59  the_krow
# IPTC
#
# Revision 1.4  2003/05/13 15:00:23  the_krow
# Tiff parsing
#
# Revision 1.3  2003/05/13 12:31:11  the_krow
# + GNU Copyright Notice
# + PNG Parsing
#
# -----------------------------------------------------------------------
# MMPython - Media Metadata for Python
# Copyright (C) 2003 Thomas Schueppel
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
# 
# -----------------------------------------------------------------------
#endif


import mediainfo
import IPTC
import EXIF
import struct

# interesting file format info:
# http://www.dcs.ed.ac.uk/home/mxr/gfx/2d-hi.html

SOF = { 0xC0 : "Baseline",   
        0xC1 : "Extended sequential",   
        0xC2 : "Progressive",   
        0xC3 : "Lossless",   
        0xC5 : "Differential sequential",   
        0xC6 : "Differential progressive",   
        0xC7 : "Differential lossless",   
        0xC9 : "Extended sequential, arithmetic coding",   
        0xCA : "Progressive, arithmetic coding",   
        0xCB : "Lossless, arithmetic coding",   
        0xCD : "Differential sequential, arithmetic coding",   
        0xCE : "Differential progressive, arithmetic coding",   
        0xCF : "Differential lossless, arithmetic coding",
}

class JPGInfo(mediainfo.ImageInfo):

    def __init__(self,file):
        mediainfo.ImageInfo.__init__(self)
        self.iptc = None        
        self.mime = 'image/jpeg'
        self.type = 'jpeg image'
        self.valid = 1
        if file.read(2) != '\xff\xd8':
            self.valid = 0
            return
        file.seek(-2,2)
        if file.read(2) != '\xff\xd9':
            self.valid = 0
            return
        file.seek(2)
        app = file.read(4)
        while (len(app) == 4):
            (ff,segtype,seglen) = struct.unpack(">BBH", app)
            if ff != 0xff: break
            print "SEGMENT: 0x%x%x, len=%d" % (ff,segtype,seglen)
            if segtype == 0xd9:
                break
            elif SOF.has_key(segtype):
                data = file.read(seglen-2)
                (precision,self.height,self.width,num_comp) = struct.unpack('>BHHB', data[:6])
                print "H/W: %i / %i" % (self.height, self.width) 
            elif segtype == 0xed:
                app = file.read(seglen-2)
                self.iptc = IPTC.flatten(IPTC.parseiptc(app))
                break
            else:
                file.seek(seglen-2,1)
            app = file.read(4)
        file.seek(0)        
        self.exif = EXIF.process_file(file)
        if self.exif:
            self.setitem( 'comment', self.exif, 'EXIF UserComment' )
#            self.setitem( 'width', self.exif, 'EXIF ExifImageWidth'  )
#            self.setitem( 'height', self.exif, 'EXIF ExifImageLength' )
            self.setitem( 'date', self.exif, 'Image DateTime' )            
            self.setitem( 'artist', self.exif, 'Image Artist' )
            self.setitem( 'hardware', self.exif, 'Image Model' )
            self.setitem( 'software', self.exif, 'Image Software' )
#            self.setitem( 'thumbnail', self.exif, 'JPEGThumbnail' ) 
        if self.iptc:
            self.setitem( 'title', self.iptc, 517 ) 
            self.setitem( 'date' , self.iptc, 567 )
            self.setitem( 'comment', self.iptc, 617 )
            self.setitem( 'keywords', self.iptc, 537 )
            self.setitem( 'artist', self.iptc, 592 )
            self.setitem( 'country', self.iptc, 612 ) 
            self.setitem( 'caption', self.iptc, 632 )
        return
       

factory = mediainfo.get_singleton()
jpginfo = JPGInfo
factory.register( 'image/jpeg', ['jpg','jpeg'], mediainfo.TYPE_IMAGE, jpginfo )
print "jpeg type registered"
