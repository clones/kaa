#if 0 /*
# -----------------------------------------------------------------------
# lsdvdinfo.py - parse dvd title structure
# -----------------------------------------------------------------------
# $Id$
#
# Use lsdvd to get dvd informations.
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


import os
import ifoparser
from mmpython import mediainfo
import mmpython
from discinfo import DiscInfo

LSDVD_EXE='lsdvd'

class DVDAudio(mediainfo.AudioInfo):
    def __init__(self, data):
        mediainfo.AudioInfo.__init__(self)
        self.number   = int(data[1])
        if data[3] != 'xx':
            self.language = data[3]
        self.codec    = data[7]
        self.samplerate = int(data[9])
        self.channels = data[13]


class DVDVideo(mediainfo.VideoInfo):
    def __init__(self, data):
        mediainfo.VideoInfo.__init__(self)
        self.width  = int(data[12])
        self.height = int(data[14])
        self.fps    = float(data[5])
        self.aspect = data[10]


class DVDTitle(mediainfo.AVInfo):
    def __init__(self, data):
        mediainfo.AVInfo.__init__(self)
        self.number = int(data[1])

        self.keys.append('subtitles')
        self.keys.append('chapters')
        
        self.mime = 'video/mpeg'

        l = data[3].split(':')
        self.length   = (int(l[0])*60+int(l[1]))*60+int(l[2])
        self.trackno  = int(data[1])
        self.chapters = int(data[5])
        
            
class DVDInfo(DiscInfo):
    def __init__(self, device):
        DiscInfo.__init__(self)
        self.context = 'video'
        self.offset = 0
        if os.path.isdir(device):
            self.valid = self.isDVDdir(device)
        else:
            self.valid = self.isDisc(device)

        if self.valid and self.tracks:
            self.keys.append('length')
            self.length = 0
            first       = 0

            for t in self.tracks:
                self.length += t.length
                if not first:
                    first = t.length
            
            if self.length/len(self.tracks) == first:
                # badly mastered dvd
                self.length = first

        self.mime    = 'video/dvd'
        self.type    = 'DVD'
        self.subtype = 'video'


    def lsdvd(self, path):
        """
        use lsdvd to get informations about this disc
        """
        import popen2
        child = popen2.Popen3('%s -v -n -a -s "%s"' % (LSDVD_EXE, path), 1, 100)
        for line in child.fromchild.readlines():
            data = line.replace(',', '').replace('\t', '').\
                   replace('\n', '').replace('  ', ' ').split(' ')
            if len(data) > 2:
                if data[0] == 'Title:':
                    ti = DVDTitle(data)
                    self.appendtrack(ti)
                elif data[0] == 'Audio:':
                    self.tracks[-1].audio.append(DVDAudio(data))
                elif data[0] == 'Subtitle:':
                    self.tracks[-1].subtitles.append(data[3])
                elif data[0] == 'VTS:':
                    self.tracks[-1].video.append(DVDVideo(data))
                    self.tracks[-1].video[-1].length = self.tracks[-1].length
                elif data[:3] == ['Number', 'of', 'Angles:']:
                    self.tracks[-1].angles = int(data[3])
                    self.tracks[-1].keys.append('angles')
                    
        child.wait()
        child.fromchild.close()
        child.childerr.close()
        child.tochild.close()

        if len(self.tracks) > 0:
            for ti in self.tracks:
                ti.trackof = len(self.tracks)
            return 1

        return 0
    
            
    def isDVDdir(self, dirname):
        if not os.path.isdir(dirname+'/VIDEO_TS'):
            return 0

        return self.lsdvd(dirname)

    
    def isDisc(self, device):
        if DiscInfo.isDisc(self, device) != 2:
            return 0

        # brute force reading of the device to find out if it is a DVD
        f = open(device,'rb')
        f.seek(32808, 0)
        buffer = f.read(50000)

        if buffer.find('UDF') == -1:
            f.close()
            return 0

        # seems to be a DVD, read a little bit more
        buffer += f.read(550000)
        f.close()

        if buffer.find('VIDEO_TS') == -1 and buffer.find('VIDEO_TS.IFO') == -1 and \
               buffer.find('OSTA UDF Compliant') == -1:
            return 0

        return self.lsdvd(device)


if os.environ.has_key('LSDVD') and os.environ['LSDVD']:
    LSDVD_EXE = os.environ['LSDVD']
else:
    for path in os.environ['PATH'].split(':'):
        if os.path.isfile(os.path.join(path, 'lsdvd')):
            LSDVD_EXE = os.path.join(path, 'lsdvd')
            break
    else:
        if mediainfo.DEBUG:
            print 'ImportError: lsdvd not found'
        raise ImportError

mmpython.registertype( 'video/dvd', mediainfo.EXTENSION_DEVICE, mediainfo.TYPE_AV, DVDInfo )
mmpython.registertype( 'video/dvd', mediainfo.EXTENSION_DIRECTORY,
                       mediainfo.TYPE_AV, DVDInfo )
