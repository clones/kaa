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
import mmpython
import discinfo
import DiscID
import CDDB
import cdrom

_debug = mediainfo._debug

class AudioDiscInfo(discinfo.DiscInfo):
    def __init__(self,device):
        discinfo.DiscInfo.__init__(self)
        self.context = 'audio'
        self.offset = 0
        self.valid = self.isDisc(device)
        self.mime = 'audio/cd'
        self.type = 'CD'
        self.subtype = 'audio'
        

    def isDisc(self, device):
        if discinfo.DiscInfo.isDisc(self, device) != 1:
            return 0
        
        disc_id = DiscID.disc_id(device)
        (query_stat, query_info) = CDDB.query(disc_id)

        if query_stat == 210 or query_stat == 211:
            # set this to success
            query_stat = 200
            for i in query_info:
                if i['title'] != i['title'].upper():
                    query_info = i
                    break
            else:
                query_info = query_info[0]

        elif query_stat != 200:
            _debug("failure getting disc info, status %i" % query_stat)


        
        if query_stat == 200:
            qi = query_info['title'].split('/')
            self.artist = qi[1].strip()
            self.title = qi[0].strip()
            (read_stat, read_info) = CDDB.read(query_info['category'], 
                                               query_info['disc_id'])
            # id = disc_id + number of tracks
            self.id = '%s_%s' % (query_info['disc_id'], disc_id[1])

            if read_stat == 210:
                for i in range(0, disc_id[1]):
                    mi = mediainfo.MusicInfo()
                    mi.title = read_info['TTITLE' + `i`]
                    mi.album = self.title
                    mi.artist = self.artist
                    mi.genre = query_info['category']
                    mi.codec = 'PCM'
                    mi.samplerate = 44.1
                    mi.trackno = i+1
                    mi.trackof = disc_id[1]
                    self.tracks.append(mi)
            else:
                _debug("failure getting track info, status: %i" % read_stat)
                # set query_stat to somthing != 200
                query_stat = 400
            

        if query_stat != 200:
            _debug("failure getting disc info, status %i" % query_stat)
            for i in range(0, disc_id[1]):
                mi = mediainfo.MusicInfo()
                mi.title = 'Track %s' % (i+1)
                mi.codec = 'PCM'
                mi.samplerate = 44.1
                mi.trackno = i+1
                mi.trackof = disc_id[1]
                self.tracks.append(mi)
                
                
        # read the tracks to generate the title list
        device = open(device)
        (first, last) = cdrom.toc_header(device)

        lmin = 0
        lsec = 0

        num = 0
        for i in range(first, last + 2):
            if i == last + 1:
                min, sec, frames = cdrom.leadout(device)
            else:
                min, sec, frames = cdrom.toc_entry(device, i)
            if num:
                self.tracks[num-1].length = (min-lmin)*60 + (sec-lsec)
            num += 1
            lmin, lsec = min, sec
        device.close()
        return 1
    
        
mmpython.registertype( 'audio/cd', mediainfo.EXTENSION_DEVICE, mediainfo.TYPE_AUDIO, AudioDiscInfo )
