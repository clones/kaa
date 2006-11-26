# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# flacinfo.py - flac file parser
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
#
# First Edition: Thomas Schueppel <stain@acm.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
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
# -----------------------------------------------------------------------------

# python imports
import struct
import re
import logging

# kaa imports
from kaa.metadata import mediainfo
from kaa.metadata import factory
import ogginfo

# get logging object
log = logging.getLogger('metadata')

# See: http://flac.sourceforge.net/format.html

class FlacInfo(mediainfo.MusicInfo):
    def __init__(self,file):
        mediainfo.MusicInfo.__init__(self)
        if file.read(4) != 'fLaC':
            raise mediainfo.KaaMetadataParseError()

        while 1:
            (blockheader,) = struct.unpack('>I',file.read(4))
            lastblock = (blockheader >> 31) & 1
            type = (blockheader >> 24) & 0x7F
            numbytes = blockheader & 0xFFFFFF
            log.debug("Last?: %d, NumBytes: %d, Type: %d" % \
                      (lastblock, numbytes, type))
            # Read this blocks the data
            data = file.read(numbytes)
            if type == 0:
                # STREAMINFO
                bits = struct.unpack('>L', data[10:14])[0]
                self.samplerate = (bits >> 12) & 0xFFFFF
                self.channels = ((bits >> 9) & 7) + 1
                self.samplebits = ((bits >> 4) & 0x1F) + 1
                md5 = data[18:34]
            elif type == 1:
                # PADDING
                pass
            elif type == 2:
                # APPLICATION
                pass
            elif type == 3:
                # SEEKTABLE
                pass
            elif type == 4:
                # VORBIS_COMMENT
                skip, self.vendor = self._extractHeaderString(data)
                num, = struct.unpack('<I', data[skip:skip+4])
                start = skip+4
                header = {}
                for i in range(num):
                    (nextlen, s) = self._extractHeaderString(data[start:])
                    start += nextlen
                    a = re.split('=',s)
                    header[(a[0]).upper()]=a[1]
                if header.has_key('TITLE'):
                    self.title = header['TITLE']
                if header.has_key('ALBUM'):
                    self.album = header['ALBUM']
                if header.has_key('ARTIST'):
                    self.artist = header['ARTIST']
                if header.has_key('COMMENT'):
                    self.comment = header['COMMENT']
                if header.has_key('DATE'):
                    self.date = header['DATE']
                if header.has_key('ENCODER'):
                    self.encoder = header['ENCODER']
                if header.has_key('TRACKNUMBER'):
                    self.trackno = header['TRACKNUMBER']

                self.appendtable('VORBISCOMMENT', header)
            elif type == 5:
                # CUESHEET
                pass
            else:
                # UNKNOWN TYPE
                pass
            if lastblock:
                break

    def _extractHeaderString(self,header):
        len = struct.unpack( '<I', header[:4] )[0]
        return (len+4,unicode(header[4:4+len], 'utf-8'))


factory.register( 'application/flac', ('flac',), mediainfo.TYPE_MUSIC,
                  FlacInfo )
