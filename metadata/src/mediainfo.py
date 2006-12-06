# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# mediainfo.py
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
#
# First Edition: Thomas Schueppel <stain@acm.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
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
# -----------------------------------------------------------------------------

# python imports
import os
import logging
import copy
import sys

# kaa imports
from kaa.strutils import str_to_unicode, unicode_to_str

# fourcc list for debugging
import fourcc

UNPRINTABLE_KEYS = [ 'thumbnail']

# type definitions
TYPE_NONE      = 0
TYPE_AUDIO     = 1
TYPE_VIDEO     = 2
TYPE_IMAGE     = 4
TYPE_AV        = 5
TYPE_MUSIC     = 6
TYPE_HYPERTEXT = 8
TYPE_MISC      = 10

MEDIACORE = ['title', 'caption', 'comment', 'size', 'type', 'subtype', 'date',
             'keywords', 'country', 'language', 'url', 'media', 'artist']

AUDIOCORE = ['channels', 'samplerate', 'length', 'encoder', 'codec', 'format',
             'samplebits', 'bitrate', 'fourcc' ]

VIDEOCORE = ['length', 'encoder', 'bitrate', 'samplerate', 'codec', 'format',
             'samplebits', 'width', 'height', 'fps', 'aspect', 'trackno', 'fourcc' ]

MUSICCORE = ['trackno', 'trackof', 'album', 'genre', 'discs', 'thumbnail' ]

AVCORE    = ['length', 'encoder', 'trackno', 'trackof', 'copyright', 'product',
             'genre', 'writer', 'producer', 'studio', 'rating', 'starring',
             'delay', 'image', 'video', 'audio', 'subtitles', 'chapters' ]

EXTENSION_DEVICE    = 'device'
EXTENSION_DIRECTORY = 'directory'
EXTENSION_STREAM    = 'stream'

# get logging object
log = logging.getLogger('metadata')


class KaaMetadataParseError:
    pass


class MediaInfo(object):
    """
    MediaInfo is the base class to all Media Metadata Containers. It defines
    the basic structures that handle metadata. MediaInfo and its derivates
    contain a common set of metadata attributes that is listed in keys.
    Specific derivates contain additional keys to the dublin core set that is
    defined in MediaInfo.
    """
    _keys = MEDIACORE
    table_mapping = {}

    def __init__(self, hash=None):
        if hash is not None:
            # create mediainfo based on dict
            for key, value in hash.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    value = [ MediaInfo(x) for x in value ]
                self._set(key, value)
            return
        
        self._keys = self._keys[:]
        self._tables = {}
        for key in self._keys:
            setattr(self, key, None)


    #
    # unicode and string convertion for debugging
    #

    def __unicode__(self):
        result = u''

        # print normal attributes
        lists = []
        for key in self._keys:
            value = getattr(self, key, None)
            if value == None or key == 'url':
                continue
            if isinstance(value, list):
                if value:
                    lists.append((key, value))
                continue
            if key in UNPRINTABLE_KEYS:
                value = '<unprintable data>'
            result += u'  %10s: %s\n' % (unicode(key), unicode(value))

        # print lists
        for key, l in lists:
            result += u'\n  %5s list:' % key
            for item in l:
                result += '\n    ' + unicode(item).replace('\n', '\n    ') + u'\n'

        # print tables
        if log.level >= 10:
            for name, table in self._tables.items():
                result += '\n\n    Table %s' % str(name)
                for key, value in table.items():
                    try:
                        value = unicode(value)
                        if len(value) > 50:
                            value = '<unprintable data>'
                    except UnicodeDecodeError:
                        value = '<unprintable data>'
                    result += '\n        %s: %s' % (unicode(key), unicode(value))
        return result


    def __str__(self):
        return unicode_to_str(unicode(self))


    def __repr__(self):
        return '<%s %s>' % (str(self.__class__)[8:-2], self.url)


    #
    # internal functions
    #

    def _appendtable(self, name, hashmap):
        """
        Appends a tables of additional metadata to the Object.
        If such a table already exists, the given tables items are
        added to the existing one.
        """
        if not self._tables.has_key(name):
            self._tables[name] = hashmap
        else:
            # Append to the already existing table
            for k in hashmap.keys():
                self._tables[name][k] = hashmap[k]


    def _set(self, key, value):
        """
        Set key to value and add the key to the internal keys list if
        missing.
        """
        if value is None and getattr(self, key, None) is None:
            return
        if isinstance(value, str):
            value = str_to_unicode(value)
        setattr(self, key, value)
        if not key in self._keys:
            self._keys.append(key)


    def _finalize(self):
        """
        Correct same data based on specific rules
        """
        # make sure all strings are unicode
        for key in self._keys:
            if key in UNPRINTABLE_KEYS:
                continue
            value = getattr(self, key)
            if value is None:
                continue
            if isinstance(value, str):
                setattr(self, key, str_to_unicode(value))
            if isinstance(value, unicode):
                setattr(self, key, value.strip().rstrip().replace(u'\0', u''))
            if isinstance(value, list) and value and isinstance(value[0], MediaInfo):
                for submenu in value:
                    submenu._finalize()

        # copy needed tags from tables
        for name, table in self._tables.items():
            mapping = self.table_mapping.get(name, {})
            for tag, attr in mapping.items():
                value = table.get(tag, None)
                if value is not None:
                    if not isinstance(value, (str, unicode)):
                        value = unicode(str(value))
                    elif isinstance(value, str):
                        value = str_to_unicode(value)
                    value = value.strip().rstrip().replace(u'\0', u'')
                    setattr(self, attr, value)

    #
    # data access
    #

    def __contains__(self, key):
        """
        Test if key exists in the dict
        """
        return hasattr(self, key)


    def get(self, key, default = None):
        """
        Returns key in dict, otherwise defaults to 'default' if key doesn't
        exist.
        """
        return getattr(self, key, default)


    def __getitem__(self, key):
        """
        get the value of 'key'
        """
        return getattr(self, key, None)


    def __setitem__(self, key, value):
        """
        set the value of 'key' to 'value'
        """
        setattr(self, key, value)


    def has_key(self, key):
        """
        check if the object has a key 'key'
        """
        return hasattr(self, key)


    def convert(self):
        """
        Convert mediainfo to dict.
        """
        result = {}
        for k in self._keys:
            value = getattr(self, k, None)
            if isinstance(value, list) and value and isinstance(value[0], MediaInfo):
                value = [ x.convert() for x in value ]
            result[k] = value
        return result


    def keys(self):
        """
        Return all keys.
        """
        return self._keys


class AudioInfo(MediaInfo):
    """
    Audio Tracks in a Multiplexed Container.
    """
    _keys = MediaInfo._keys + AUDIOCORE
    media = 'audio'

    def _finalize(self):
        if self.codec is not None:
            self.fourcc, self.codec = fourcc.resolve(self.codec)


class MusicInfo(AudioInfo):
    """
    Digital Music.
    """
    _keys = AudioInfo._keys + MUSICCORE
    media = 'audio'

    def _finalize(self):
        """
        Correct same data based on specific rules
        """
        AudioInfo._finalize(self)
        if self.trackof:
            try:
                # XXX Why is this needed anyway?
                if int(self.trackno) < 10:
                    self.trackno = '0%s' % int(self.trackno)
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
            except:
                pass


class VideoInfo(MediaInfo):
    """
    Video Tracks in a Multiplexed Container.
    """
    _keys = MediaInfo._keys + VIDEOCORE
    media = 'video'

    def _finalize(self):
        if self.codec is not None:
            self.fourcc, self.codec = fourcc.resolve(self.codec)


class ChapterInfo(MediaInfo):
    """
    Chapter in a Multiplexed Container.
    """
    _keys = ['name', 'pos', 'enabled']

    def __init__(self, name="", pos=0):
        MediaInfo.__init__(self)
        self.name = name
        self.pos = pos
        self.enabled = True


class SubtitleInfo(MediaInfo):
    """
    Subtitle Tracks in a Multiplexed Container.
    """
    _keys = ['language', 'trackno', 'title']
    media = 'subtitle'

    def __init__(self, language=None):
        MediaInfo.__init__(self)
        self.language = language

        
class AVInfo(MediaInfo):
    """
    Container for Audio and Video streams. This is the Container Type for
    all media, that contain more than one stream.
    """
    _keys = MediaInfo._keys + AVCORE

    def __init__(self):
        MediaInfo.__init__(self)
        self.audio = []
        self.video = []
        self.subtitles = []
        self.chapters  = []


    def _finalize(self):
        """
        Correct same data based on specific rules
        """
        MediaInfo._finalize(self)
        if not self.length and len(self.video) and self.video[0].length:
            self.length = self.video[0].length
        for container in [ self ] + self.video + self.audio:
            if container.length:
                container.length = int(container.length)


class CollectionInfo(MediaInfo):
    """
    Collection of Digial Media like CD, DVD, Directory, Playlist
    """
    _keys = MediaInfo._keys + [ 'id', 'tracks' ]

    def __init__(self):
        MediaInfo.__init__(self)
        self.tracks = []
