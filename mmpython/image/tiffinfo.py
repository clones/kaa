#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.4  2003/05/13 15:52:43  the_krow
# Caption added
#
# Revision 1.3  2003/05/13 15:23:59  the_krow
# IPTC
#
# Revision 1.2  2003/05/13 15:16:02  the_krow
# width+height hacked
#
# Revision 1.1  2003/05/13 15:00:23  the_krow
# Tiff parsing
#
# -----------------------------------------------------------------------
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
import struct

MOTOROLASIGNATURE = 'MM\x00\x2a'
INTELSIGNATURE = 'II\x2a\x00'

# http://partners.adobe.com/asn/developer/pdfs/tn/TIFF6.pdf

class TIFFInfo(mediainfo.ImageInfo):

    def __init__(self,file):
        mediainfo.ImageInfo.__init__(self)
        self.iptc = None        
        self.mime = 'image/tiff'
        self.type = 'TIFF image'
        self.intel = 0
        self.valid = 0
        header = file.read(8)
        if header[:4] == MOTOROLASIGNATURE:
#            print "motorola"
            self.valid = 1
            self.intel = 0
            (offset,) = struct.unpack(">I", header[4:8])
#            print "offset: %i" % offset
            file.seek(offset)
            (len,) = struct.unpack(">H", file.read(2))
#            print "tiff motorola, len=%d" % len
            app = file.read(len*12)
            for i in range(len):
                (tag, type, length, value, offset) = struct.unpack('>HHIHH', app[i*12:i*12+12])
                print "[%i/%i] tag: 0x%.4x, type 0x%.4x, len %d, value %d, offset %d)" % (i,len,tag,type,length,value,offset)
                if tag == 0x8649:
                    file.seek(offset,0)
                    self.iptc = IPTC.flatten(IPTC.parseiptc(file.read(1000)))
                elif tag == 0x0100:
                    if value != 0:
                        self.width = value
                    else:
                        self.width = offset
                elif tag == 0x0101:
                    if value != 0:
                        self.height = value
                    else:
                        self.height = offset

        elif header[:4] == INTELSIGNATURE:
            print "intel"
            self.valid = 1
            self.intel = 1
            (offset,) = struct.unpack("<I", header[4:8])
#            print "offset: %i" % offset
            file.seek(offset,0)
            (len,) = struct.unpack("<H", file.read(2))
#            print "tiff intel, len=%d" % len
            app = file.read(len*12)
            for i in range(len):
                (tag, type, length, offset, value) = struct.unpack('<HHIHH', app[i*12:i*12+12])
                print "[%i/%i] tag: 0x%.4x, type 0x%.4x, len %d, value %d, offset %d)" % (i,len,tag,type,length,value,offset)
                if tag == 0x8649:
                    file.seek(offset)
                    self.iptc = IPTC.flatten(IPTC.parseiptc(file.read(1000)))
                elif tag == 0x0100:
                    if value != 0:
                        self.width = value
                    else:
                        self.width = offset
                elif tag == 0x0101:
                    if value != 0:
                        self.height = value
                    else:
                        self.height = offset
        else:
            return
            
        if self.iptc:
            self.setitem( 'title', self.iptc, 517 ) 
            self.setitem( 'date' , self.iptc, 567 )
            self.setitem( 'comment', self.iptc, 617 )
            self.setitem( 'keywords', self.iptc, 537 )
            self.setitem( 'artist', self.iptc, 592 )
            self.setitem( 'country', self.iptc, 612 ) 
            self.setitem( 'caption', self.iptc, 632 )

            

factory = mediainfo.get_singleton()
tiffinfo = TIFFInfo
factory.register( 'image/tiff', ['tif','tiff'], mediainfo.TYPE_IMAGE, tiffinfo )
print "tiff type registered"
