#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.27  2003/06/09 14:31:56  the_krow
# fixes on the mpeg parser
# resolutions, fps and bitrate should be reported correctly now
#
# Revision 1.26  2003/06/09 12:50:07  the_krow
# mp3 now fills tables
#
# Revision 1.25  2003/06/09 12:28:10  dischi
# build better id for disc-caching
#
# Revision 1.24  2003/06/09 11:46:16  the_krow
# DVDInfo changes
# Output changes
#
# Revision 1.23  2003/06/09 11:19:27  the_krow
# Bugfixes concerning CollectionInfo
# Audio CD infos added
#
# Revision 1.22  2003/06/08 19:59:53  dischi
# make the code smaller
#
# Revision 1.21  2003/06/08 19:55:54  dischi
# added bins metadata support
#
# Revision 1.20  2003/06/08 16:49:48  dischi
# Added a list for unprintable keys we don't want to see when converting
# to string (right now only thumbnail, it's very ugly). Also added
# __setitem__ and has_key for better access as dict.
#
# Revision 1.19  2003/06/08 15:42:00  dischi
# cosmetic stuff
#
# Revision 1.18  2003/06/08 13:44:22  dischi
# import table again, sorry
#
# Revision 1.17  2003/06/08 13:40:09  the_krow
# table added
#
# Revision 1.16  2003/06/08 13:17:44  dischi
# some cleanup
#
# Revision 1.15  2003/06/08 13:14:14  dischi
# added DEBUG flag and moved the register print to the register function
#
# Revision 1.14  2003/06/08 11:30:22  the_krow
# *** empty log message ***
#
# Revision 1.13  2003/06/08 11:23:06  the_krow
# added Collection Type for Media Collection like Audio CDS, DVDs, VCDs
#
# Revision 1.12  2003/06/08 10:24:07  dischi
# Added subdir disc
#
# Revision 1.11  2003/06/07 23:10:49  the_krow
# Changed mp3 into new format.
#
# Revision 1.10  2003/06/07 22:54:28  the_krow
# AVInfo stuff added.
#
# Revision 1.9  2003/06/07 21:41:05  the_krow
# Changed MediaInfo Objects to new structure. AV is used for av streams and
# consists of a list of video and audio information.
#
# Revision 1.8  2003/06/07 16:02:48  dischi
# Added dvd support and make a correct package from mmpython
#
# Revision 1.7  2003/05/13 17:49:41  the_krow
# IPTC restructured\nEXIF Height read correctly\nJPEG Endmarker read
#
# Revision 1.6  2003/05/13 15:52:41  the_krow
# Caption added
#
# Revision 1.5  2003/05/13 15:23:59  the_krow
# IPTC
#
# Revision 1.4  2003/05/13 12:31:43  the_krow
# + Copyright Notice
#
# -----------------------------------------------------------------------
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


TYPE_NONE = 0
TYPE_AUDIO = 1
TYPE_VIDEO = 2
TYPE_IMAGE = 4
TYPE_AV = 5
TYPE_MUSIC = 6
TYPE_HYPERTEXT = 8

import string
import types
import os
import stat
import table
import traceback

from image import bins

import re
from fcntl import ioctl


DEBUG = 1

# Audiocore: TITLE, CAPTION, ARTIST, TRACKNO, TRACKOF, ALBUM, CHANNELS, SAMPLERATE, TYPE, SUBTYPE, LENGTH, ENCODER
#  + ID3 Tags
#  + ID3V2 Tags
#  + Ogg Vorbis Headers
#  + CDDB
#  + Filename / Directory
# Videocore: TITLE, LENGTH, ENCODER, CHANNELS, TYPE, SUBTYPE, DATE
#  + IMDB
#  + Freevo XML Info
#  + Filename / Directory
# Imagecore: TITLE, ARTIST (=PHOTOGRAPHER), TYPE, SUBTYPE, X, Y, COLORS, 
#  + EXIF (in TIFF, JPG)
#  + IPTC (in TIFF, JPG)
#  + Filename
#  + PNG Metadata
# Module variable that contains an initialized MetaDataFactory() object

_singleton = None

def _debug(text):
    if DEBUG > 1: print text

def get_singleton():
    global _singleton

    # One-time init
    if _singleton == None:
        _singleton = SynchronizedObject(MetaDataFactory())
        if DEBUG: print _singleton
        
    return _singleton


MEDIACORE = ['title', 'caption', 'comment', 'artist', 'size', 'type', 'subtype',
             'date', 'keywords', 'country', 'language']
AUDIOCORE = ['channels', 'samplerate', 'length', 'encoder', 'codec', 'samplebits',
             'bitrate', 'language']
VIDEOCORE = ['length', 'encoder', 'bitrate', 'samplerate', 'codec', 'samplebits',
             'width', 'height', 'fps']
IMAGECORE = ['description', 'people', 'location', 'event',
             'width','height','thumbnail','software','hardware']
MUSICCORE = ['trackno', 'trackof', 'album', 'genre']
AVCORE    = ['length', 'encoder', 'trackno', 'trackof', 'copyright', 'product',
             'genre', 'secondary genre', 'subject', 'writer', 'producer', 
             'cinematographer', 'production designer', 'edited by', 'costume designer',
             'music by', 'studio', 'distributed by', 'rating', 'starring', 'ripped by',
             'digitizing date', 'internet address', 'source form', 'medium', 'source',
             'archival location', 'commisioned by', 'engineer', 'cropped', 'sharpness',
             'dimensions', 'lightness', 'dots per inch', 'palette setting',
             'default audio stream', 'logo url', 'watermark url', 'info url',
             'banner image', 'banner url', 'infotext']

DEVICE    = 'device'

UNPRINTABLE_KEYS = [ 'thumbnail', ]

import table

class MediaInfo:
    def __init__(self):
        self.keys = []
        self.tables = {}
        for k in MEDIACORE:
            setattr(self,k,None)
            self.keys.append(k)

    def __str__(self):
        import copy
        keys = copy.copy(self.keys)

        for k in UNPRINTABLE_KEYS:
            if k in keys:
                keys.remove(k)

        result = reduce( lambda a,b: self[b] and "%s\n        %s: %s" % \
                         (a, b.__str__(), self[b].__str__()) or a, keys, "" )
        try:
            for i in self.tables.keys():
                 result += self.tables[i].__str__()
        except AttributeError:
            pass
        return result            
        
    def appendtable(self, name, hashmap):
        self.tables[name] = table.Table(hashmap, name)
    
    def setitem(self,item,dict,key):
        try:
            if self.__dict__.has_key(item):
                self.__dict__[item] = dict[key]
            else:
                _debug("Unknown key: %s" % item)
        except:
            pass

    def __getitem__(self,key):
        return self.__dict__[key]

    def __setitem__(self, key, val):
        self.__dict__[key] = val

    def has_key(self, key):
        return self.__dict__.has_key(key)


class AudioInfo(MediaInfo):
    def __init__(self):
        self.keys = []
        for k in AUDIOCORE:
            setattr(self,k,None)
            self.keys.append(k)

class MusicInfo(AudioInfo):
    def __init__(self):
        MediaInfo.__init__(self)
        for k in AUDIOCORE+MUSICCORE:
            setattr(self,k,None)
            self.keys.append(k)

class VideoInfo(MediaInfo):
    def __init__(self):
        self.keys = []
        for k in VIDEOCORE:
            setattr(self,k,None)
            self.keys.append(k)
           

class AVInfo(MediaInfo):
    def __init__(self):
        MediaInfo.__init__(self)
        for k in AVCORE:
            setattr(self,k,None)
            self.keys.append(k)
        self.audio = []
        self.video = []
        self.subtitles = []
        
    def __str__(self):
        result = "Attributes:"
        result += MediaInfo.__str__(self)
        if len(self.video) + len(self.audio) + len(self.subtitles) > 0:
            result += "\n Stream list:"
            if len(self.video):
                result += reduce( lambda a,b: a + "  \n   Video Stream:" + b.__str__(),
                                  self.video, "" )
            if len(self.audio):
                result += reduce( lambda a,b: a + "  \n   Audio Stream:" + b.__str__(),
                                  self.audio, "" )
            if len(self.subtitles):
                result += reduce( lambda a,b: a + "  \n   Subtitle Stream:" + b.__str__(),
                                  self.subtitles, "" )
            return result

        
class ImageInfo(MediaInfo):
    def __init__(self):
        MediaInfo.__init__(self)        
        for k in IMAGECORE:
            setattr(self,k,None)
            self.keys.append(k)

    def add_bins_data(self, filename):
	if os.path.isfile(filename + '.xml'):
            try:
                binsinfo = bins.get_bins_desc(filename)
                for key in IMAGECORE + MEDIACORE:
                    for bins_type in ('desc', 'exif'):
                        if not self[key] and binsinfo[bins_type].has_key(key):
                            self[key] = binsinfo[bins_type][key]
            except:
                pass


class CollectionInfo(MediaInfo):
    def __init__(self):
        MediaInfo.__init__(self)
        self.tracks = []
        self.keys.append('id')
        self.id = None

    def __str__(self):
        result = MediaInfo.__str__(self)
        result += "\nTrack list:"
        for counter in range(0,len(self.tracks)):
             result += " \nTrack %d:\n%s" % (counter+1, self.tracks[counter])
        return result
    
    def appendtrack(self, track):
        self.tracks.append(track)


class DiscInfo(CollectionInfo):
    def isDisc(self, device):

        CDROM_DRIVE_STATUS=0x5326
        CDSL_CURRENT=( (int ) ( ~ 0 >> 1 ) )
        CDROM_DISC_STATUS=0x5327
        CDS_AUDIO=100
        CDS_MIXED=105

        try:
            fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
            s = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT)
        except:
            # maybe we need to close the fd if ioctl fails, maybe
            # open fails and there is no fd
            try:
                os.close(fd)
            except:
                pass
            return 0

        s = ioctl(fd, CDROM_DISC_STATUS)
        os.close(fd)
        if s == CDS_AUDIO or s == CDS_MIXED:
            return 1
        
        f = open(device,'rb')

        f.seek(0x0000832d)
        self.id = f.read(16)
        f.seek(32808, 0)
        self.label = f.read(32)
        f.close()

        m = re.match("^(.*[^ ]) *$", self.label)
        if m:
            self.label = m.group(1)
            self.id    = '%s_%s' % (self.id, self.label)
        else:
            self.label = ''
            self.id    = '%s_NO_LABEL' % self.id

        self.keys.append('label')
        return 2

    
class MetaDataFactory:
    def __init__(self):
        self.extmap = {}
        self.types = []
        self.device_types = []
        
    def create_from_file(self,file,filename):
        # Check extension as a hint
        for e in self.extmap.keys():
            if DEBUG: print "trying %s" % e
            if filename and filename.find(e) >= 0:
                file.seek(0,0)
                t = self.extmap[e][3](file, filename)
                if t.valid: return t

        if DEBUG: print "No Type found by Extension. Trying all"
        for e in self.types:
            if DEBUG: print "Trying %s" % e[0]
            try:
                t = e[3](file, filename)
                if t.valid: return t
            except:
                if DEBUG:
                    traceback.print_exc()
        return None

    def create_from_url(self,url):
        pass
        
    def create_from_filename(self,filename):
        print filename
        if stat.S_ISBLK(os.stat(filename)[stat.ST_MODE]):
            r = self.create_from_device(filename)
        elif os.path.isfile(filename):
            f = open(filename,'rb')
            r = self.create_from_file(f,filename)
            f.close()
        else:
            r = None
        return r

    def create_from_device(self,devicename):
        for e in self.device_types:
            if DEBUG: print 'Trying %s' % e[0]
            t = e[3](devicename)
            if t.valid: return t
        return None
            
    def register(self,mimetype,extensions,type,c):
        if DEBUG: print "%s registered" % mimetype
        tuple = (mimetype,extensions,type,c)
        if extensions == DEVICE:
            self.device_types.append(tuple)
        else:
            self.types.append(tuple)
            for e in extensions:
                self.extmap[e] = tuple
        

#
# synchronized objects and methods.
# By André Bjärby
# From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65202
# 
from types import *
def _get_method_names (obj):
    if type(obj) == InstanceType:
        return _get_method_names(obj.__class__)
    
    elif type(obj) == ClassType:
        result = []
        for name, func in obj.__dict__.items():
            if type(func) == FunctionType:
                result.append((name, func))

        for base in obj.__bases__:
            result.extend(_get_method_names(base))

        return result


class _SynchronizedMethod:

    def __init__ (self, method, obj, lock):
        self.__method = method
        self.__obj = obj
        self.__lock = lock

    def __call__ (self, *args, **kwargs):
        self.__lock.acquire()
        try:
            #print 'Calling method %s from obj %s' % (self.__method, self.__obj)
            return self.__method(self.__obj, *args, **kwargs)
        finally:
            self.__lock.release()

class SynchronizedObject:    
    def __init__ (self, obj, ignore=[], lock=None):
        import threading

        self.__methods = {}
        self.__obj = obj
        lock = lock and lock or threading.RLock()
        for name, method in _get_method_names(obj):
            if not name in ignore:
                self.__methods[name] = _SynchronizedMethod(method, obj, lock)

    def __getattr__ (self, name):
        try:
            return self.__methods[name]
        except KeyError:
            return getattr(self.__obj, name)


if __name__ == '__main__':
    import ogginfo
    t = _singleton.create_from_filename('7.ogg')
    print t
