#!/usr/bin/python
#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.25  2003/11/07 13:58:52  dischi
# extra check for dvd
#
# Revision 1.24  2003/09/22 16:24:58  the_krow
# o added flac
# o try-except block around ioctl since it is not avaiable in all OS
#
# Revision 1.23  2003/09/14 13:50:42  dischi
# make it possible to scan extention based only
#
# Revision 1.22  2003/09/10 18:41:44  dischi
# add USE_NETWORK, maybe there is no network connection
#
# Revision 1.21  2003/09/01 18:54:12  dischi
# add callback for cache_dir
#
# Revision 1.20  2003/08/26 13:16:41  outlyer
# Enabled m4a support
#
# Revision 1.19  2003/07/10 11:17:35  the_krow
# ogminfo is used to parse ogg files
#
# Revision 1.18  2003/07/01 21:07:42  dischi
# switch back to eyed3info
#
# Revision 1.17  2003/06/30 13:17:18  the_krow
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

# Do this stuff before importing the info instances since they 
# depend on this function

import factory

from synchronizedobject import SynchronizedObject

_factory = None

def Factory():
    global _factory

    # One-time init
    if _factory == None:
        _factory = SynchronizedObject(factory.Factory())
        
    return _factory

def registertype(mimetype,extensions,type,c):
    f = Factory()
    f.register(mimetype,extensions,type,c)    


# Okay Regular imports and code follow

import sys
import os
import mediainfo
#import audio.ogginfo
import audio.pcminfo
import audio.m4ainfo
import video.riffinfo
import video.mpeginfo
import video.asfinfo
import video.movinfo
import image.jpginfo
import image.pnginfo
import image.tiffinfo
import video.vcdinfo
import video.realinfo
import video.ogminfo
try:
    import disc.discinfo
    import disc.vcdinfo
    import disc.audioinfo
    import disc.datainfo
except ImportError:
    pass

try:
    import disc.dvdinfo
except ImportError:
    pass

import audio.eyed3info
#import audio.mp3info
import audio.webradioinfo
import audio.flacinfo



try:
    import cache
except ImportError:
    pass
    

USE_NETWORK     = 1
object_cache    = None
uncachable_keys = [ 'thumbnail', ]


def use_cache(directory):
    """
    use directory to search for cached results
    """
    global object_cache
    if not os.path.isdir(directory):
        print 'WARNING: cache directory %s doesn\'t exists, caching deactivated' % directory
        return 0
    object_cache = cache.Cache(directory)


def check_cache(directory):
    """
    Return how many files in this directory are not in the cache. It's
    possible to guess how much time the update will need.
    """
    global object_cache
    if not object_cache:
        return -1
    return object_cache.check_cache(directory)


def cache_dir(directory, uncachable_keys = uncachable_keys, callback=None, ext_only = 0):
    """
    cache every file in the directory for future use
    """
    global object_cache
    if not object_cache:
        return {}
    return object_cache.cache_dir(directory, uncachable_keys, callback, ext_only)


def parse(filename, bypass_cache = 0, ext_only = 0):
    """
    parse the file
    """
    global object_cache

    if object_cache and not bypass_cache:
        try:
            return object_cache.find(filename)
        except cache.FileNotFoundException:
            pass
    info = Factory().create(filename, ext_only)
    if info and object_cache and isinstance(info, disc.discinfo.DiscInfo):
        object_cache.cache_disc(info)
    return info

