#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.1  2003/06/23 22:23:16  the_krow
# First Import. Not yet integrated.
#
#
# -----------------------------------------------------------------------
# MMPython - Media Metadata for Python
# Copyright (C) 2003 Thomas Schueppel, Dirk Meyer
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

import urllib
import struct

from mmpython import mediainfo

_print = mediainfo._debug

class WebRadioInfo(mediainfo.MusicInfo):
    def __init__(self,file):
        mediainfo.MusicInfo.__init__(self)
        # http://205.188.209.193:80/stream/1006
        header = file.readlines(4096)
        if header[0][:10] == 'ICY 200 OK':
            self.valid = 1
        else:
            self.valid = 0
            return
        # Read until a line that is only \r\n
        for index in range(0,len(header)):
            if header[index] == '\r\n':
                break
                
        tags = map(lambda x: x.rstrip('\r\n'), header[1:index])
        tab = {}
        for t in tags:
            a,b = t.split(': ')
            tab[a] = b
        self.appendtable('ICY', tab)
        self.bitrate = tab['icy-br']
        self.title = tab['icy-name']
        self.genre = tab['icy-genre']
        

factory = mediainfo.get_singleton()
factory.register( 'application/webradio', ('',), mediainfo.TYPE_MUSIC, WebRadioInfo )
