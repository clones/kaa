#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.2  2003/06/24 12:59:33  the_krow
# Added Webradio.
# Added Stream Type to mediainfo
#
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

import urlparse
import string
import urllib

from mmpython import mediainfo

_print = mediainfo._debug

# http://205.188.209.193:80/stream/1006

ICY_tags = { 'title': 'icy-name',
             'genre': 'icy-genre',
             'bitrate': 'icy-br',
             'caption': 'icy-url',
           }

class WebRadioInfo(mediainfo.MusicInfo):
    def __init__(self, url):
        mediainfo.MusicInfo.__init__(self)
        tup = urlparse.urlsplit(url)
        scheme, location, path, query, fragment = tup
        if scheme != 'http':
            self.valid = 0
            return
        # Open an URL Connection
        fi = urllib.urlopen(url)
        

        # grab the statusline
        self.statusline = fi.readline()
        try:
            statuslist = string.split(self.statusline)
        except ValueError:
            # assume it is okay since so many servers are badly configured
            statuslist = ["ICY", "200"]
    
        if statuslist[1] == "302":
            # moved temporarily status, look for location header
            while 1:
                line = fi.readline()
                if not line:
                    self.valid = 0
                    return
            if string.find(line, "Location") == 0:
                location = line[10:]              
                # strip leading and trailing whitespace
                location = string.strip(self.location)
    
        elif statuslist[1] != "200":
            self.valid = 0
            return

        self.valid = 1
        self.type = 'audio'
        self.subtype = 'mp3'
        # grab any headers for a max of 10 lines
        linecnt = 0
        tab = {}
        lines = fi.readlines(512)        
        while linecnt < 10:
            icyline = lines[linecnt]
            icyline = icyline.rstrip('\r\n')
            linecnt += 1
            if len(icyline) < 4:
                break
            cidx = icyline.find(':')
            if cidx != -1:                
                # break on short line (ie. really should be a blank line)
                # strip leading and trailing whitespace                
                tab[icyline[:cidx].strip()] = icyline[cidx+2:].strip()
        if fi:
            fi.close()
        self.appendtable('ICY', tab)
        self.tag_map = { 'ICY' : ICY_tags }
        # Copy Metadata from tables into the main set of attributes        
        for k in self.tag_map.keys():
            if self.tables.has_key(k):
                map(lambda x:self.setitem(x,self.tables[k],self.tag_map[k][x]), self.tag_map[k].keys())        
        self.bitrate = string.atoi(self.bitrate)*1000        

factory = mediainfo.get_singleton()
factory.register( 'text/plain', mediainfo.STREAM, mediainfo.TYPE_MUSIC, WebRadioInfo )

