#!/usr/bin/env python
# Based on a sample implementation posted to daap-dev mailing list by
# Bob Ippolito <bob@redivi.com>
#
# Modifed by Aubin Paul <aubin@outlyer.org> for mmpython/Freevo
#

import struct
from mmpython import mediainfo
import mmpython

_print = mediainfo._debug

class Mpeg4(mediainfo.MusicInfo):
    containerTags = ('moov', 'udta', 'trak', 'mdia', 'minf', 'dinf', 'stbl', 'meta', 'ilst', '----')
    skipTags = {'meta':4 }

    def __init__(self, file):
        mediainfo.MusicInfo.__init__(self)
        #self.f = open(fn)
        self.f = file
        self.valid = 1
        returnval = 0
        while returnval == 0:
            try:
                self.readNextTag()
            except ValueError:
                returnval = 1
        if mediainfo.DEBUG:
            self.output()

    def readNextTag(self):
        length, name = self.readInt(), self.read(4)
        length -= 8
        if length < 0:
            raise ValueError, "Oops?"
        #print "%r" % str(name) # (%r bytes, starting at %r)" % (name, length, self.f.tell() + 8)
        if name in self.containerTags:
            self.read(self.skipTags.get(name, 0))
            data = '[container tag]'
        else:
            data = self.read(length)
        if name == '\xa9nam':
            self.title = data[8:]
        if name == '\xa9ART':
            self.artist = data[8:]
        if name == '\xa9alb':
            self.album = data[8:]
        if name == 'trkn':
            # Fix this
            self.trackno = data
        if name == '\xa9day':
            self.year = data[8:]
        if name == '\xa9too':
            self.encoder = data[8:]
        return 0
        #return name, data
        
    def read(self, b):
        data = self.f.read(b)
        if len(data) < b:
            raise ValueError, "EOF"
        return data

    def readInt(self):
        return struct.unpack('>I', self.read(4))[0]
        

    def output(self):
        print self.title
        print self.artist
        print self.album
        print self.year
        print self.encoder
        #print self.trackno # No track numbers yet

mmpython.registertype( 'application/m4a', ('m4a',), mediainfo.TYPE_MUSIC, Mpeg4 )

