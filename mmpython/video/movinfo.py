#if 0
# $Id$
# $Log$
# Revision 1.19  2004/03/02 20:48:21  dischi
# fix gettable
#
# Revision 1.18  2003/08/30 09:36:22  dischi
# turn off some debug based on DEBUG
#
# Revision 1.17  2003/07/02 11:17:30  the_krow
# language is now part of the table key
#
# Revision 1.16  2003/06/30 13:17:20  the_krow
# o Refactored mediainfo into factory, synchronizedobject
# o Parsers now register directly at mmpython not at mmpython.mediainfo
# o use mmpython.Factory() instead of mmpython.mediainfo.get_singleton()
# o Bugfix in PNG parser
# o Renamed disc.AudioInfo into disc.AudioDiscInfo
# o Renamed disc.DataInfo into disc.DataDiscInfo
#
# Revision 1.15  2003/06/29 18:30:56  dischi
# length is broken, deactivated it until it is fixed
#
# Revision 1.14  2003/06/29 11:59:35  dischi
# make some debug silent
#
# Revision 1.13  2003/06/20 19:17:22  dischi
# remove filename again and use file.name
#
# Revision 1.12  2003/06/20 14:53:05  the_krow
# Metadata are copied from Quicktime Userdata to MediaInfo fields. This
#  may be broken since it assumes the Quicktime Comment language to be
#  set to 0.
#
# Revision 1.11  2003/06/19 17:31:12  dischi
# error handling (and nonsense data)
#
# Revision 1.10  2003/06/12 18:53:18  the_krow
# OGM detection added.
# .ram is a valid extension to real files
#
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
import mmpython
from mmpython import mediainfo
from movlanguages import *


class MovInfo(mediainfo.AVInfo):
    def __init__(self,file):
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
        else:
            return
        # Extended size
        if size == 1:
            #print "Extended Size"
            size = struct.unpack('>Q', file.read(8))                  
        while self._readatom(file):
            pass
        try:
            info = self.gettable('QTUDTA', 'en')
            self.setitem('title', info, 'nam')
            self.setitem('artist', info, 'aut')
            self.setitem('copyright', info, 'cpy')
        except OSError:
            pass
            
                
    def _readatom(self, file):
        s = file.read(8)
        if len(s) < 8:
            return 0
        atomsize,atomtype = struct.unpack('>I4s', s)
        if not str(atomtype).decode('latin1').isalnum():
            # stop at nonsense data
            return 0

        if mediainfo.DEBUG: print "%s [%X]" % (atomtype,atomsize)
        if atomtype == 'udta':
            # Userdata (Metadata)
            pos = 0
            tabl = {}
            i18ntabl = {}
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
                        i18ntabl[lang] = i18ntabl.get(lang, {})
                        i18ntabl[lang][datatype[1:]] = atomdata[mypos+4:mypos+tlen+4]
                        #['%d_%s'%(lang,datatype[1:])] = atomdata[mypos+4:mypos+tlen+4]
                        mypos += tlen+4
                elif datatype == 'WLOC':
                    # Drop Window Location
                    pass
                else:
                    tabl[datatype] = atomdata[pos+8:pos+datasize]
#                print "%s: %s" % (datatype, tabl[datatype])
                pos += datasize
            if len(i18ntabl.keys()) > 0:
                for k in i18ntabl.keys():                
                    self.appendtable('QTUDTA', i18ntabl[k], QTLANGUAGES[k])
                    self.appendtable('QTUDTA', tabl, QTLANGUAGES[k])
            else:
                #print "NO i18"
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
                    # XXX length is broken, it report days (!) when you interpret
                    # XXX the length as seconds
                    #self.length = vi.length = tkhd[5]
                                        
                    # XXX Date number of Seconds is since January 1st 1904!!!
                    self.date = tkhd[1]
                    self.video.append(vi)
                    #print tkhd
                pos += datasize
        elif atomtype == 'mdat':
            while self._readatom(file):
                pass
            #if atomsize == 0:
            #    file.seek(0,2)
            #else:
            #    file.seek(atomsize-8,1)
        else:
            # Skip unknown atoms
            try:
                file.seek(atomsize-8,1)
            except IOError:
                return 0
        return 1 
        
mmpython.registertype( 'video/quicktime', ('mov', 'qt'), mediainfo.TYPE_AV, MovInfo )
