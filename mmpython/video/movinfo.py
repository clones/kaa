#if 0
# $Id$
# $Log$
# Revision 1.9  2003/06/12 16:56:53  the_krow
# Some Quicktime should work.
#
# Revision 1.8  2003/06/12 15:58:05  the_krow
# QT parsing of i18n metadata
#
# Revision 1.7  2003/06/12 14:43:22  the_krow
# Realmedia file parsing. Title, Artist, Copyright work. Couldn't find
# many technical parameters to retrieve.
# Some initial QT parsing
# added Real to __init__.py
#
# Revision 1.6  2003/06/08 19:53:21  dischi
# also give the filename to init for additional data tests
#
# Revision 1.5  2003/06/08 15:40:26  dischi
# catch exception, raised for small text files
#
# Revision 1.4  2003/06/08 13:44:58  dischi
# Changed all imports to use the complete mmpython path for mediainfo
#
# Revision 1.3  2003/06/08 13:11:38  dischi
# removed print at the end and moved it into register
#
# Revision 1.2  2003/05/13 12:31:43  the_krow
# + Copyright Notice
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

import re
import struct
import string
import fourcc

from mmpython import mediainfo

class MovInfo(mediainfo.AVInfo):
    def __init__(self,file,filename):
        mediainfo.AVInfo.__init__(self)
        self.context = 'video'
        self.valid = 0
        self.mime = 'video/quicktime'
        self.type = 'Quicktime Video'
        h = file.read(8)                
        (size,type) = struct.unpack('>I4s',h)
        if type == 'moov':
            self.valid = 1
        elif type == 'wide':
            self.valid = 1
        # Extended size
        if size == 1:
            print "Extended Size"
            size = struct.unpack('>Q', file.read(8))                  
        while self._readatom(file):
            pass
            
                
    def _readatom(self, file):
        s = file.read(8)
        if len(s) < 8:
            return 0
        atomsize,atomtype = struct.unpack('>I4s', s)
        print "%s [%d]" % (atomtype,atomsize)        
        if atomtype == 'udta':
            # Userdata (Metadata)
            pos = 0
            tabl = {}
            atomdata = file.read(atomsize-8)
            while pos < atomsize-12:
                (datasize,datatype) = struct.unpack('>I4s', atomdata[pos:pos+8])
                if ord(datatype[0]) == 169:
                    # i18n Metadata... 
                    mypos = 8+pos
                    while mypos < datasize+pos:
                        # first 4 Bytes are i18n header
                        (tlen,lang) = struct.unpack('>HH', atomdata[mypos:mypos+4])
                        #print "%d %d/%d %s" % (lang,tlen,datasize,atomdata[mypos+4:mypos+tlen+4])
                        tabl['%d_%s'%(lang,datatype[1:])] = atomdata[mypos+4:mypos+tlen+4]
                        mypos += tlen+4
                elif datatype == 'WLOC':
                    # Drop Window Location
                    pass
                else:
                    tabl[datatype] = atomdata[pos+8:pos+datasize]
#                print "%s: %s" % (datatype, tabl[datatype])
                pos += datasize
            self.appendtable('QTUDTA', tabl)
        elif atomtype == 'trak':
            atomdata = file.read(atomsize-8)
            pos = 0
            while pos < atomsize-8:
                (datasize,datatype) = struct.unpack('>I4s', atomdata[pos:pos+8])
                #print "%s [%d]" % (datatype, datasize)
                if datatype == 'tkhd':
                    tkhd = struct.unpack('>6I8x4H36xII', atomdata[pos+8:pos+datasize])
                    vi = mediainfo.VideoInfo()
                    vi.width = tkhd[10] >> 16
                    vi.height = tkhd[11] >> 16
                    vi.id = tkhd[3]
                    self.length = vi.length = tkhd[5]
                    self.date = tkhd[1]
                    self.video.append(vi)
                    print tkhd
                pos += datasize
        else:
            # Skip unknown atoms
            atomdata = file.seek(atomsize-8,1)
        return 1 
        
factory = mediainfo.get_singleton()  
factory.register( 'video/quicktime', ('mov', 'qt'), mediainfo.TYPE_AV, MovInfo )
