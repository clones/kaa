#if 0 /*
# -----------------------------------------------------------------------
# audioinfo.py - support for audio cds
# -----------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------
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
# ----------------------------------------------------------------------- */
#endif


from mmpython import mediainfo
import DiscID
import CDDB

_debug = mediainfo._debug

class AudioInfo(mediainfo.DiscInfo):
    def __init__(self,device):
        mediainfo.DiscInfo.__init__(self)
        self.context = 'audio'
        self.offset = 0
        self.valid = self.isDisc(device)
        self.mime = 'audio/cd'
        self.type = 'audio cd'
        

    def isDisc(self, device):
        if mediainfo.DiscInfo.isDisc(self, device) != 1:
            return 0
        
        cdrom = DiscID.open(device)
        disc_id = DiscID.disc_id(cdrom)
        
        (query_stat, query_info) = CDDB.query(disc_id)

        if query_stat == 210 or query_stat == 211:
            for i in query_info:
                if i['title'] != i['title'].upper():
                    query_info = i
                    break
            else:
                query_info = query_info[0]
                         
        elif query_stat != 200:
            _debug("failure getting disc info, status %i" % query_stat)
            return 1

        self.title = query_info['title']
        (read_stat, read_info) = CDDB.read(query_info['category'], 
                                           query_info['disc_id'])
        for key in query_info:
            setattr(self, key, query_info[key])
            if not key in self.keys:
                self.keys.append(key)

        if read_stat == 210:
            for i in range(0, disc_id[1]):
                mi = mediainfo.MusicInfo()
                mi.title = read_info['TTITLE' + `i`]
                mi.album = query_info['title']
                mi.genre = query_info['category']
                mi.codec = 'PCM'
                mi.samplerate = 44100
                mi.trackno = i+1
                mi.trackof = disc_id[1]
                self.tracks.append(mi)
        else:
            _debug("failure getting track info, status: %i" % read_stat)

        return 1
    
        
factory = mediainfo.get_singleton()  
factory.register( 'audio/cd', mediainfo.DEVICE, mediainfo.TYPE_AUDIO, AudioInfo )
