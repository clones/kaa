#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.49  2003/06/30 13:17:18  the_krow
# o Refactored mediainfo into factory, synchronizedobject
# o Parsers now register directly at mmpython not at mmpython.mediainfo
# o use mmpython.Factory() instead of mmpython.mediainfo.get_singleton()
# o Bugfix in PNG parser
# o Renamed disc.AudioInfo into disc.AudioDiscInfo
# o Renamed disc.DataInfo into disc.DataDiscInfo
#
# Revision 1.48  2003/06/30 11:38:00  dischi
# catch exception
#
# Revision 1.47  2003/06/29 18:29:02  dischi
# small fixes
#
# Revision 1.46  2003/06/24 12:59:33  the_krow
# Added Webradio.
# Added Stream Type to mediainfo
#
# Revision 1.45  2003/06/24 10:09:51  dischi
# o improved URL parsing to support cd: scheme
# o added function create to mediainfo who calls the needed create_from
#
# Revision 1.44  2003/06/23 22:35:08  the_krow
# Started working on create_from_url
#
# Revision 1.43  2003/06/23 20:59:11  the_krow
# PNG should now fill a correct table.
#
# Revision 1.42  2003/06/23 20:48:11  the_krow
# width + height fixes for OGM files
#
# Revision 1.41  2003/06/23 09:22:54  the_krow
# Typo and Indentation fixes.
#
# Revision 1.40  2003/06/21 15:27:42  dischi
# some debug and added url (e.g. filename) to the key list
#
# Revision 1.39  2003/06/20 19:17:21  dischi
# remove filename again and use file.name
#
# Revision 1.38  2003/06/20 19:04:34  dischi
# search for VobSub subtitles
#
# Revision 1.37  2003/06/20 14:43:57  the_krow
# Putting Metadata into MediaInfo from AVIInfo Table
#
# Revision 1.36  2003/06/20 14:17:26  dischi
# fix indent
#
# Revision 1.35  2003/06/20 09:24:17  the_krow
# Documentation
#
# Revision 1.34  2003/06/19 17:30:07  dischi
# small bugfix, always return results
#
# Revision 1.33  2003/06/11 20:50:59  the_krow
# Title, Artist and some other data sucessfully parsed from wmv, asf, wma
#
# Revision 1.32  2003/06/10 22:16:07  dischi
# support for cd://-URLs added
#
# Revision 1.31  2003/06/10 16:04:17  the_krow
# reference to DiscItem in cache was still pointing to mediainfo
# visuals
#
# Revision 1.30  2003/06/10 10:56:53  the_krow
# - Build try-except blocks around disc imports to make it run on platforms
#   not compiling / running the C extensions.
# - moved DiscInfo class to disc module
# - changed video.VcdInfo to be derived from CollectionInfo instead of
#   DiskInfo so it can be used without the cdrom extensions which are
#   hopefully not needed for bin-files.
#
# Revision 1.29  2003/06/09 23:13:06  the_krow
# bugfix: unknown files are now resetted before trying if they are valid
# first rudimentary eyed3 mp3 parser added
#
# Revision 1.28  2003/06/09 16:12:30  dischi
# make the disc ids like the one from Freevo
#
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

import string
import types
import table
import traceback

from image import bins


import re
import urllib
import urlparse
import os

MEDIACORE = ['title', 'caption', 'comment', 'artist', 'size', 'type', 'subtype',
             'date', 'keywords', 'country', 'language', 'url']
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


UNPRINTABLE_KEYS = [ 'thumbnail', ]

import table

import mmpython

EXTENSION_DEVICE    = 'device'
EXTENSION_STREAM    = 'stream'

DEBUG     = 1

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

        result = ''
        result += reduce( lambda a,b: self[b] and "%s\n        %s: %s" % \
                         (a, b.__str__(), self[b].__str__()) or a, keys, "" )
        try:
            for i in self.tables.keys():
                 result += self.tables[i].__str__()
        except AttributeError:
            pass
        return result
        
    def appendtable(self, name, hashmap):
        """
        Appends a tables of additional metadata to the Object. 
        """
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
        try:
            if isinstance(self.__dict__[key], str):
                return self.__dict__[key].strip().rstrip().replace('\0', '')
            return self.__dict__[key]
        except KeyError:
            return None
        
    def __setitem__(self, key, val):
        self.__dict__[key] = val

    def has_key(self, key):
        return self.__dict__.has_key(key)

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

    