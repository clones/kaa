#if 0
# -----------------------------------------------------------------------
# mkvinfo.py - Matroska Streaming Video Files
# -----------------------------------------------------------------------
# $Id$
#
# $Log$
# Revision 1.1  2004/01/31 12:24:15  dischi
# add basic matroska info
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


from mmpython import mediainfo
import mmpython
import struct
import re
import stat
import os
import math
from types import *
from struct import *
from string import *

_print = mediainfo._debug

# Main IDs for the Matroska streams
MATROSKA_HEADER_ID       = '\x1A\x45\xDF\xA3'
MATROSKA_TRACKS_ID       = '\x16\x54\xAE\x6B'
MATROSKA_SEGMENT_ID      = '\x18\x53\x80\x67'
MATROSKA_SEEK_HEAD_ID    = '\x11\x4D\x9B\x74'
MATROSKA_SEGMENT_INFO_ID = '\x15\x49\xA9\x66'
MATROSKA_CLUSTER_ID      = '\x1F\x43\xB6\x75'
MATROSKA_VOID_ID         = '\xEC'
MATROSKA_CRC_ID          = '\xBF'
MATROSKA_VIDEO_TYPE_ID   = '\x83'
MATROSKA_CODEC_ID        = '\x86'
MATROSKA_CODEC_NAME_ID   = '\x25\x86\x88'
MATROSKA_FRAME_DURATION_ID = '\x23\xE3\x83'
MATROSKA_VIDEO_SETTINGS_ID = '\xE0'
MATROSKA_VID_WIDTH_ID      = '\xB0'
MATROSKA_VID_HEIGHT_ID     = '\xBA'
MATROSKA_AUDIO_SETTINGS_ID = '\xE1'
MATROSKA_AUDIO_SAMPLERATE_ID = '\xB5'
MATROSKA_AUDIO_CHANNELS_ID   = '\x9F'
MATROSKA_TRACK_LANGUAGE_ID   = '\x22\xB5\x9C'
MATROSKA_TIMECODESCALE_ID    = '\x2A\xD7\xB1'
MATROSKA_DURATION_ID         = '\x44\x89'
MATROSKA_MUXING_APP_ID       = '\x4D\x80'
MATROSKA_WRITING_APP_ID      = '\x57\x41'

MATROSKA_VIDEO_TRACK = 1
MATROSKA_AUDIO_TRACK = 2

# This is class that is responsible to handle one Ebml entity as described in the Matroska/Ebml spec
class EbmlEntity:
    def __init__(self, inbuf):
        # Compute the EBML id
        self.compute_id(inbuf)
        #_print("Entity id : %08X" % self.entity_id)
        if ( self.id_len == 0):
            self.valid = 0
            _print("EBML entity not found, bad file format")
            return
        self.valid = 1
        self.entity_len = self.compute_len(inbuf[self.id_len:])
        # Obviously, the segment can be very long (ie the whole file, so we truncate it at the read buffer size
        if (self.entity_len == -1):
            self.entity_data = inbuf[self.id_len+self.len_size:]
            self.entity_len = len(self.entity_data) # Set the remaining size
        else:
            self.entity_data = inbuf[self.id_len+self.len_size:self.id_len+self.len_size+self.entity_len]
        #_print("Entity len : %d" % self.entity_len)
        # if the size is 1, 2 3 or 4 it could be a numeric value, so do the job
        self.value = 0
        if self.entity_len == 1:
            self.value = ord(self.entity_data[0])
        if self.entity_len == 2:
            self.value = unpack('!H', self.entity_data)[0]
        if self.entity_len == 3:
            self.value = ord(self.entity_data[0])<<16 | ord(self.entity_data[1])<<8 | ord(self.entity_data[2])
        if self.entity_len == 4:
            self.value = unpack('!I', self.entity_data)[0]

    def compute_id(self, inbuf):
        first = ord(inbuf[0])
        self.id_len = 0
        if (first & 0x80):
            self.id_len = 1
            self.entity_id = first
        elif (first & 0x40):
            self.id_len = 2
            self.entity_id = ord(inbuf[0])<<8 | ord(inbuf[1])
        elif (first & 0x20):
            self.id_len = 3
            self.entity_id = (ord(inbuf[0])<<16) | (ord(inbuf[1])<<8) | (ord(inbuf[2]))
        elif (first & 0x10):
            self.id_len = 4
            self.entity_id = (ord(inbuf[0])<<24) | (ord(inbuf[1])<<16) | (ord(inbuf[2])<<8) | (ord(inbuf[3]))
        self.entity_str = inbuf[0:self.id_len]
        return

    def compute_len(self, inbuf):
        # Here we just handle the size up to 4 bytes
        # The size above will be truncated by the read buffer itself
        first = ord(inbuf[0])
        if (first & 0x80):
            self.len_size = 1
            return first - 0x80
        if (first & 0x40):
            self.len_size = 2
            (c1,c2) = unpack('BB',inbuf[:2])
            return ((c1-0x40)<<8) | (c2)
        if (first & 0x20):
            self.len_size = 3
            (c1, c2, c3) = unpack('BBB',inbuf[:3])
            return ((c1-0x20)<<16) | (c2<<8) | (c3)
        if (first & 0x10):
            self.len_size = 4
            (len) = unpack('!I',inbuf[:4])
            return len
        if (first & 0x08):
            self.len_size = 5
            return -1
        if (first & 0x04):
            self.len_size = 6
            return -1
        if (first & 0x02):
            self.len_size = 7
            return -1
        if (first & 0x01):
            self.len_size = 8
            return -1

    def get_value(self):
        value = self.value
        return value

    def get_data(self):
        return self.entity_data

    def get_id(self):
        return self.entity_id

    def get_str_id(self):
        return self.entity_str

    def get_len(self):
        return self.entity_len

    def get_total_len(self):
        return self.entity_len+self.id_len+self.len_size


# This ithe main Matroska object
class MkvInfo(mediainfo.AVInfo):
    def __init__(self, file):
        mediainfo.AVInfo.__init__(self)
        self.samplerate = 1

        buffer = file.read(80000)
        if len(buffer) == 0:
            # Regular File end
            return None

        # Check the Matroska header
        header = EbmlEntity(buffer)
        if ( header.get_str_id() == MATROSKA_HEADER_ID ):
            _print("HEADER ID found %08X" % header.get_id() )
            self.valid = 1
            self.mime = 'application/mkv'
            self.type = 'Matroska'
            # Now get the segment
            segment = EbmlEntity(buffer[header.get_total_len():])
            if ( segment.get_str_id() == MATROSKA_SEGMENT_ID):
                #MEDIACORE = ['title', 'caption', 'comment', 'artist', 'size', 'type', 'subtype',
                #'date', 'keywords', 'country', 'language', 'url']
                segtab = self.process_one_level(segment)
                seginfotab = self.process_one_level(segtab[MATROSKA_SEGMENT_INFO_ID])
                try:
                    scalecode = seginfotab[MATROSKA_TIMECODESCALE_ID].get_value()
                except:
                    scalecode = 1000
                try:
                    duration = unpack('!f', seginfotab[MATROSKA_DURATION_ID].get_data() )[0]
                    duration = duration / scalecode
                    self.length = duration
                except:
                    pass
                try:
                    entity = segtab[MATROSKA_TRACKS_ID]
                    self.process_tracks(entity)
                except:
                    _print("TRACKS ID not found !!" )
            else:
                _print("SEGMENT ID not found %08X" % segment.get_id() )
        else:
            self.valid = 0

    def process_tracks(self, tracks):
        tracksbuf = tracks.get_data()
        indice = 0
        while indice < tracks.get_len():
            trackelem = EbmlEntity(tracksbuf[indice:])
            self.process_one_track(trackelem)
            indice += trackelem.get_total_len()

    def process_one_level(self, item):
        buf = item.get_data()
        indice = 0
        tabelem = {}
        while indice < item.get_len():
            elem = EbmlEntity(buf[indice:])
            tabelem[elem.get_str_id()] = elem
            #print "Found elem %s" % elem.get_str_id()
            indice += elem.get_total_len()
        return tabelem

    def process_one_track(self, track):
        # Process all the items at the track level
        tabelem = self.process_one_level(track)
        # We have the dict of track eleme, now build the MMPYTHON information
        type = tabelem[MATROSKA_VIDEO_TYPE_ID]
        if (type.get_value() == MATROSKA_VIDEO_TRACK ):
            #VIDEOCORE = ['length', 'encoder', 'bitrate', 'samplerate', 'codec', 'samplebits',
            #     'width', 'height', 'fps', 'aspect']
            vi = mediainfo.VideoInfo()
            try:
                elem = tabelem[MATROSKA_CODEC_ID]
                vi.codec = elem.get_data()
            except:
                vi.codec = 'Unknown'
            try:
                elem = tabelem[MATROSKA_FRAME_DURATION_ID]
                vi.fps = 1 / (pow(10, -9) * (elem.get_value()))
            except:
                vi.fps = 0
            try:
                vinfo = tabelem[MATROSKA_VIDEO_SETTINGS_ID]
                vidtab = self.process_one_level(vinfo)
                vi.width  = vidtab[MATROSKA_VID_WIDTH_ID].get_value()
                vi.height = vidtab[MATROSKA_VID_HEIGHT_ID].get_value()
            except:
                _print("No info about video track !!!")
            self.video.append(vi)
        elif (type.get_value() == MATROSKA_AUDIO_TRACK ):
            #AUDIOCORE = ['channels', 'samplerate', 'length', 'encoder', 'codec', 'samplebits',
            #     'bitrate', 'language']
            ai = mediainfo.AudioInfo()
            try:
                elem = tabelem[MATROSKA_TRACK_LANGUAGE_ID]
                ai.language = elem.get_data()
            except:
                ai.language = 'Unknown'
            try:
                elem = tabelem[MATROSKA_CODEC_ID]
                ai.codec = elem.get_data()
            except:
                ai.codec = 'Unknown'
            try:
                ainfo = tabelem[MATROSKA_AUDIO_SETTINGS_ID]
                audtab = self.process_one_level(vinfo)
                ai.samplerate  = unpack('!f', audtab[MATROSKA_AUDIO_SAMPLERATE_ID].get_value())[0]
                ai.channels = audtab[MATROSKA_AUDIO_CHANNELS_ID].get_value()
            except:
                _print("No info about audio track !!!")
            self.audio.append(ai)

        _print("Found %d elem for this track" % len(tabelem) )

mmpython.registertype( 'application/mkv', ('mkv', 'mka',), mediainfo.TYPE_AV, MkvInfo )