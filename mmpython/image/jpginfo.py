#if 0
# $Id$
# $Log$
# Revision 1.3  2003/05/13 12:31:11  the_krow
# + GNU Copyright Notice
# + PNG Parsing
#
#
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

# interesting file format info:
# http://www.dcs.ed.ac.uk/home/mxr/gfx/2d-hi.html


class JPGInfo(mediainfo.ImageInfo):

    def __init__(self,file):
        mediainfo.ImageInfo.__init__(self)
        self.iptc = None        
        self.mime = 'image/jpeg'
        self.type = 'jpeg image'
        self.iptc = IPTC.getiptcinfo(file)
        self.valid = 1
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
            self.setitem( 'title', self.iptc, 517 ) 
            self.setitem( 'date' , self.iptc, 567 )
            self.setitem( 'comment', self.iptc, 617 )
            self.setitem( 'keywords', self.iptc, 537 )
            self.setitem( 'artist', self.iptc, 592 )
            self.setitem( 'country', self.iptc, 612 ) 
        self.height = self.exif.keys()
        return
       

factory = mediainfo.get_singleton()
jpginfo = JPGInfo
factory.register( 'image/jpeg', ['jpg','jpeg'], mediainfo.TYPE_IMAGE, jpginfo )
print "jpeg type registered"