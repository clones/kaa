#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.61  2004/05/27 08:59:50  dischi
# fix chapters printing
#
# Revision 1.60  2004/05/20 15:55:08  dischi
# add xml file detection
#
# Revision 1.59  2004/05/18 21:54:49  dischi
# add chapter support
#
# Revision 1.58  2004/05/17 19:10:57  dischi
# better DEBUG handling
#
# Revision 1.57  2004/05/12 18:41:42  dischi
# include all tags in desc from bins
#
# Revision 1.56  2004/02/04 19:14:11  dischi
# add attributes to list of getable items
#
# Revision 1.55  2004/02/03 20:41:18  dischi
# add directory support
#
# Revision 1.54  2003/10/04 14:30:08  dischi
# add audio delay for avi
#
# Revision 1.53  2003/08/05 17:22:58  dischi
# add doc and __delitem__
#
# Revision 1.52  2003/07/19 11:38:19  dischi
# turn off debug as default, some exception handling
#
# Revision 1.51  2003/07/07 21:35:47  dischi
# added aspect to VIDEOCORE
#
# Revision 1.50  2003/07/02 11:17:29  the_krow
# language is now part of the table key
#
# Revision 1.49  2003/06/30 13:17:18  the_krow
# o Refactored mediainfo into factory, synchronizedobject
# o Parsers now register directly at mmpython not at mmpython.mediainfo
# o use mmpython.Factory() instead of mmpython.mediainfo.get_singleton()
# o Bugfix in PNG parser
# o Renamed disc.AudioInfo into disc.AudioDiscInfo
# o Renamed disc.DataInfo into disc.DataDiscInfo
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


TYPE_NONE = 0
TYPE_AUDIO = 1
TYPE_VIDEO = 2
TYPE_IMAGE = 4
TYPE_AV = 5
TYPE_MUSIC = 6
TYPE_HYPERTEXT = 8
TYPE_MISC = 10

import string
import types
import table
import traceback

import re
import urllib
import urlparse
import os

MEDIACORE = ['title', 'caption', 'comment', 'artist', 'size', 'type', 'subtype',
             'date', 'keywords', 'country', 'language', 'url']
AUDIOCORE = ['channels', 'samplerate', 'length', 'encoder', 'codec', 'samplebits',
             'bitrate', 'language']
VIDEOCORE = ['length', 'encoder', 'bitrate', 'samplerate', 'codec', 'samplebits',
             'width', 'height', 'fps', 'aspect']
IMAGECORE = ['description', 'people', 'location', 'event',
             'width','height','thumbnail','software','hardware', 'dpi']
MUSICCORE = ['trackno', 'trackof', 'album', 'genre']
AVCORE    = ['length', 'encoder', 'trackno', 'trackof', 'copyright', 'product',
             'genre', 'secondary genre', 'subject', 'writer', 'producer', 
             'cinematographer', 'production designer', 'edited by', 'costume designer',
             'music by', 'studio', 'distributed by', 'rating', 'starring', 'ripped by',
             'digitizing date', 'internet address', 'source form', 'medium', 'source',
             'archival location', 'commisioned by', 'engineer', 'cropped', 'sharpness',
             'dimensions', 'lightness', 'dots per inch', 'palette setting',
             'default audio stream', 'logo url', 'watermark url', 'info url',
             'banner image', 'banner url', 'infotext', 'delay']


UNPRINTABLE_KEYS = [ 'thumbnail', ]

import table

import mmpython

EXTENSION_DEVICE    = 'device'
EXTENSION_DIRECTORY = 'directory'
EXTENSION_STREAM    = 'stream'

DEBUG = 0

try:
    DEBUG = int(os.environ['MMPYTHON_DEBUG'])
except:
    pass

def _debug(text):
    """
    Function for debug prints of MediaItem implementations.
    """
    if DEBUG > 1: print text
    
class MediaInfo:
    """
    MediaInfo is the base class to all Media Metadata Containers. It defines the 
    basic structures that handle metadata. MediaInfo and its derivates contain
    a common set of metadata attributes that is listed in keys. Specific derivates
    contain additional keys to the dublin core set that is defined in MediaInfo.
    MediaInfo also contains tables of addional metadata. These tables are maps
    of keys to values. The keys themselves should remain in the format that is
    defined by the metadata (I.E. Hex-Numbers, FOURCC, ...) and will be translated
    to more readable and i18nified values by an external entity.
    """
    def __init__(self):
        self.keys = []
        self._tables = {}
        for k in MEDIACORE:
            setattr(self,k,None)
            self.keys.append(k)


    def __str__(self):
        import copy
        keys = copy.copy(self.keys)

        for k in UNPRINTABLE_KEYS:
            if k in keys:
                keys.remove(k)

        result = ''
        result += reduce( lambda a,b: self[b] and b != 'url' and "%s\n        %s: %s" % \
                         (a, b.__str__(), self[b].__str__()) or a, keys, "" )
        if DEBUG:
            try:
                for i in self._tables.keys():
                    try:
                        result += self._tables[i].__str__()
                    except AttributeError:
                        pass
            except AttributeError:
                pass
        return result
        

    def appendtable(self, name, hashmap, language='en'):
        """
        Appends a tables of additional metadata to the Object. 
        If such a table already exists, the given tables items are
        added to the existing one.
        """
        if not self._tables.has_key((name, language)):
            self._tables[(name, language)] = table.Table(hashmap, name, language)
        else:
            # Append to the already existing table
            for k in hashmap.keys():
                self._tables[(name, language)][k] = hashmap[k]
    

    def gettable(self, name, language='en'):
        """
        returns a table of the given name and language        
        """
        return self._tables.get((name, language), {})
    

    def setitem(self,item,dict,key):
        """
        set item to a specific value for the dict
        """
        try:
            if self.__dict__.has_key(item):
                self.__dict__[item] = dict[key]
            else:
                _debug("Unknown key: %s" % item)
        except:
            pass


    def __getitem__(self,key):
        """
        get the value of 'key'
        """
        if self.__dict__.has_key(key):
            if isinstance(self.__dict__[key], str):
                return self.__dict__[key].strip().rstrip().replace('\0', '')
            return self.__dict__[key]
        elif hasattr(self, key):
            return getattr(self, key)
        return None

        
    def __setitem__(self, key, val):
        """
        set the value of 'key' to 'val'
        """
        self.__dict__[key] = val


    def has_key(self, key):
        """
        check if the object has a key 'key'
        """
        return self.__dict__.has_key(key) or hasattr(self, key)


    def __delitem__(self, key):
        """
        delete informations about 'key'
        """
        try:
            del self.__dict__[key]
        except:
            pass
        if hasattr(self, key):
            setattr(self, key, None)

        
class AudioInfo(MediaInfo):
    """
    Audio Tracks in a Multiplexed Container.
    """
    def __init__(self):
        self.keys = []
        for k in AUDIOCORE:
            setattr(self,k,None)
            self.keys.append(k)


class MusicInfo(AudioInfo):
    """
    Digital Music.
    """
    def __init__(self):
        MediaInfo.__init__(self)
        for k in AUDIOCORE+MUSICCORE:
            setattr(self,k,None)
            self.keys.append(k)


class VideoInfo(MediaInfo):
    """
    Video Tracks in a Multiplexed Container.
    """
    def __init__(self):
        self.keys = []
        for k in VIDEOCORE:
            setattr(self,k,None)
            self.keys.append(k)
           

class ChapterInfo(MediaInfo):
    """
    Chapter in a Multiplexed Container.
    """
    def __init__(self, name, pos=0):
        self.keys = ['name', 'pos']
        setattr(self,'name', name)
        setattr(self,'pos', pos)
           

class AVInfo(MediaInfo):
    """
    Container for Audio and Video streams. This is the Container Type for
    all media, that contain more than one stream. 
    """
    def __init__(self):
        MediaInfo.__init__(self)
        for k in AVCORE:
            setattr(self,k,None)
            self.keys.append(k)
        self.audio = []
        self.video = []
        self.subtitles = []
        self.chapters  = []

    def find_subtitles(self, filename):
        """
        Search for subtitle files. Right now only VobSub is supported
        """
        base = os.path.splitext(filename)[0]
        if os.path.isfile(base+'.idx') and os.path.isfile(base+'.sub'):
            file = open(base+'.idx')
            if file.readline().find('VobSub index file') > 0:
                line = file.readline()
                while (line):
                    if line.find('id') == 0:
                        self.subtitles.append(line[4:6])
                    line = file.readline()
            file.close()

            
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
        if not isinstance(self.chapters, int) and len(self.chapters) > 0:
            result += '\n Chapter list:'
            for i in range(len(self.chapters)):
                result += '\n   %2s: "%s" %s' % (i+1, self.chapters[i]['name'],
                                                 self.chapters[i]['pos'])
        return result

        
class ImageInfo(MediaInfo):
    """
    Digital Images, Photos, Pictures.
    """
    def __init__(self):
        MediaInfo.__init__(self)        
        for k in IMAGECORE:
            setattr(self,k,None)
            self.keys.append(k)


class CollectionInfo(MediaInfo):
    """
    Collection of Digial Media like CD, DVD, Directory, Playlist
    """
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


def get_singleton():
    print "This function is deprecated. Please use 'mmpython.Factory' instead."
    return mmpython.Factory()

    
