#if 0
# $Id$
# $Log$
# Revision 1.1  2003/05/13 12:31:11  the_krow
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
import struct
import zlib
#import Image

# interesting file format info:
# http://www.libpng.org/pub/png/png-sitemap.html#programming
# http://pmt.sourceforge.net/pngmeta/

PNGSIGNATURE = "\211PNG\r\n\032\n"

class PNGInfo(mediainfo.ImageInfo):

    def __init__(self,file):
        mediainfo.ImageInfo.__init__(self)
        self.iptc = None        
        self.mime = 'image/png'
        self.type = 'PNG image'
        self.valid = 1
        signature = file.read(8)
        signature
        
        if ( signature != PNGSIGNATURE ):
            self.valid = 0
            return
        self._readChunk(file)
        self._readChunk(file)
        self._readChunk(file)
        self._readChunk(file)
        self._readChunk(file)
        self._readChunk(file)
        self._readChunk(file)
        return       
        
    def _readChunk(self,file):
        (length, type) = struct.unpack('>I4s', file.read(8))
        if ( type == 'tEXt' ):
          print 'latin-1 Text found.'
          (data,crc) = struct.unpack('>%isI' % length,file.read(length+4))
          (key, value) = data.split('\0')
          print "%s -> %s" % (key,value)
        elif ( type == 'zTXt' ):
          print 'Compressed Text found.'
          (data,crc) = struct.unpack('>%isI' % length,file.read(length+4))
          split = data.split('\0')
          key = split[0]
          value = "".join(split[1:])          
          compression = ord(value[0])
          value = value[1:]
          if compression == 0:
              decompressed = zlib.decompress(value)
              print "%s (Compressed %i) -> %s" % (key,compression,decompressed)
          else:
              print "%s has unknown Compression %c" % (key,compression)
        elif ( type == 'iTXt' ):
          print 'International Text found.'
          (data,crc) = struct.unpack('>%isI' % length,file.read(length+4))
          (key, value) = data.split('\0')
          print "%s -> %s" % (key,value)          
        else:
          file.seek(length+4,1)
          print "%s of length %d ignored." % (type, length)
        return

factory = mediainfo.get_singleton()
pnginfo = PNGInfo
factory.register( 'image/png', ['png'], mediainfo.TYPE_IMAGE, pnginfo )
print "png type registered"