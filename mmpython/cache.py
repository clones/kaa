#if 0
# -----------------------------------------------------------------------
# cache.py - caching of mmpython objects
# -----------------------------------------------------------------------
# $Id$
#
# $Log$
# Revision 1.19  2003/07/01 21:04:07  dischi
# some fixes
#
# Revision 1.18  2003/07/01 08:24:09  the_krow
# bugfixes
#
# Revision 1.17  2003/06/30 13:17:18  the_krow
# o Refactored mediainfo into factory, synchronizedobject
# o Parsers now register directly at mmpython not at mmpython.mediainfo
# o use mmpython.Factory() instead of mmpython.mediainfo.get_singleton()
# o Bugfix in PNG parser
# o Renamed disc.AudioInfo into disc.AudioDiscInfo
# o Renamed disc.DataInfo into disc.DataDiscInfo
#
# Revision 1.16  2003/06/29 18:29:02  dischi
# small fixes
#
# Revision 1.15  2003/06/24 12:59:33  the_krow
# Added Webradio.
# Added Stream Type to mediainfo
#
# Revision 1.14  2003/06/24 10:09:51  dischi
# o improved URL parsing to support cd: scheme
# o added function create to mediainfo who calls the needed create_from
#
# Revision 1.13  2003/06/23 19:27:05  dischi
# use new (fixed) DiscID interface
#
# Revision 1.12  2003/06/21 15:41:10  dischi
# correct an error that all discs are data discs
#
# Revision 1.11  2003/06/21 15:30:13  dischi
# Special support for data discs. The cache file can be a normal disc
# cache file or a directory cache. In the second case the cache returns
# a DataDiscInfo with all files as tracks.
#
# Revision 1.10  2003/06/10 22:16:42  dischi
# added cd:// URL caching
#
# Revision 1.9  2003/06/10 16:04:17  the_krow
# reference to DiscItem in cache was still pointing to mediainfo
# visuals
#
# Revision 1.8  2003/06/10 11:50:51  dischi
# Moved all ioctl calls for discs to discinfo.cdrom_disc_status. This function
# uses try catch around ioctl so it will return 0 (== no disc) for systems
# without ioctl (e.g. Windows)
#
# Revision 1.7  2003/06/09 16:12:30  dischi
# make the disc ids like the one from Freevo
#
# Revision 1.6  2003/06/09 12:28:30  dischi
# improved disc cache
#
# Revision 1.5  2003/06/08 20:13:03  dischi
# added check_cache to get an idea how long the update will take
#
# Revision 1.4  2003/06/08 17:06:25  dischi
# cache_dir now uses the prev cache to write the cache and returns the
# list of all objects.
#
# Revision 1.3  2003/06/08 16:52:29  dischi
# Better handling for cache_disc if you don't provide a disc. Also added
# uncachable_keys to cache_dir. Caching a directory of photos all with
# exif thumbnail will slow everything down (cache filesize is 10 MB for my
# testdir, now 200 KB). Use the bypass cache option if you want all infos.
#
# Revision 1.2  2003/06/08 15:48:07  dischi
# removed some debug
#
# Revision 1.1  2003/06/08 15:38:58  dischi
# class to cache the results
#
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

import md5
import string
import os
import cPickle as pickle
import stat
import re

import mmpython
import factory

from disc import DiscID
from disc.discinfo import cdrom_disc_status, cdrom_disc_id, DiscInfo
from disc.datainfo import DataDiscInfo


class FileNotFoundException(Exception):
    pass


class Cache:
    """
    Class to cache mediainfo objects
    """
    def __init__(self, cachedir):
        self.cachedir = cachedir

        if os.path.isdir(cachedir) and not os.path.isdir('%s/disc' % cachedir):
            os.mkdir('%s/disc' % cachedir)
        self.current_objects    = None
        self.current_dir        = None
        self.CACHE_VERSION      = 1
        self.DISC_CACHE_VERSION = 1


    def hexify(self, str):
        hexStr = string.hexdigits
        r = ''
        for ch in str:
            i = ord(ch)
            r = r + hexStr[(i >> 4) & 0xF] + hexStr[i & 0xF]
        return r


    def __get_filename__(self, file):
        """
        return the cache filename for that directory/device
        """
        if stat.S_ISBLK(os.stat(file)[stat.ST_MODE]):
            id = cdrom_disc_id(file)
            if not id:
                return None
            return '%s/disc/%s' % (self.cachedir, id)
        return '%s/%s' % (self.cachedir, self.hexify(md5.new(file).digest()))
    

    def __walk_helper__(self, (result, prefix, mountpoint), dirname, names):
        for name in names:
            fullpath = os.path.join(dirname, name)[len(mountpoint)+1:]
            fullpath = '%s%s:%s' % (prefix, mountpoint, fullpath)
            result.append(fullpath)
        return result


    def __get_cachefile_and_filelist__(self, directory):
        """
        return the cachefile and the filelist for this directory
        """
        if factory.isurl(directory):
            split  = factory.url_splitter(directory)
            # this is a complete cd caching
            if split[0] == 'cd':
                device, mountpoint, filename, complete_filename = split[1:]
                cachefile = self.__get_filename__(device)
                files = []
                os.path.walk(mountpoint, self.__walk_helper__,
                             (files, 'cd://%s:' % device, mountpoint))
            else:
                return (None, None)
                
        else:
            # normal directory
            cachefile = self.__get_filename__(directory)
            files = [ os.path.join(directory, dname) for dname in os.listdir(directory) ]
            mountpoint = '/'
            
        return (cachefile, files)

    
    def check_cache(self, directory):
        """
        Return how many files in this directory are not in the cache. It's
        possible to guess how much time the update will need.
        """
        cachefile, files = self.__get_cachefile_and_filelist__(directory)

        if not cachefile:
            return -1

        new = 0
        for file in files:
            try:
                info = self.find(file)
            except FileNotFoundException:
                new += 1
        return new
    
        
    def cache_dir(self, directory, uncachable_keys):
        """
        cache every file in the directory for future use
        """
        cachefile, files = self.__get_cachefile_and_filelist__(directory)

        if not cachefile:
            return {}

        objects = {}
        for file in files:
            if factory.isurl(file):
                split = factory.url_splitter(file)
                if split[0] == 'cd':
                    device, mountpoint, filename, complete_filename = split[1:]
                    key  = '%s__%s' % (os.stat(complete_filename)[stat.ST_MTIME], filename)
                else:
                    continue
            else:
                key  = '%s__%s' % (os.stat(file)[stat.ST_MTIME], file)

            try:
                info = self.find(file)
            except FileNotFoundException:
                info = mmpython.Factory().create(file)

            if info:
                for k in uncachable_keys:
                    if info.has_key(k):
                        info[k] = None
                del info.tables
            objects[key] = info

        f = open(cachefile, 'w')
        pickle.dump((self.CACHE_VERSION, objects), f, 1)
        f.close()
        self.current_objects = objects
        return objects
    

    def cache_disc(self, info):
        """
        Adds the information 'info' about a disc into a special disc database
        """

        if not isinstance(info, DiscInfo):
            return 0

        cachefile = '%s/disc/%s' % (self.cachedir, info.id)
        f = open(cachefile, 'w')
        pickle.dump((self.DISC_CACHE_VERSION, info), f, 1)
        f.close()
        return 1

    

    def __find_disc__(self, device):
        """
        Search the cache for informations about the disc. Called from find()
        """
        disc_type = cdrom_disc_status(device)
        if disc_type == 0:
            return None
        
        elif disc_type == 1:
            disc_id = DiscID.disc_id(device)
            id = '%08lx_%d' % (disc_id[0], disc_id[1])

        else:
            f = open(device,'rb')

            f.seek(0x0000832d)
            id = f.read(16)
            f.seek(32808, 0)
            label = f.read(32)
            f.close()
            
            m = re.match("^(.*[^ ]) *$", label)
            if m:
                id    = '%s%s' % (id, m.group(1))
            
        cachefile = '%s/disc/%s' % (self.cachedir, id)
        if not os.path.isfile(cachefile):
            raise FileNotFoundException
        f = open(cachefile, 'r')
        (version, object) = pickle.load(f)
        f.close()
        if not isinstance(object, DiscInfo):
            # it's a data disc and it was cached as directory
            # build a DataDiscInfo with all files as tracks
            if not version == self.CACHE_VERSION:
                raise FileNotFoundException
            info = DataDiscInfo(device)
            for k in object:
                info.tracks.append(object[k])
            return info
        else:
            if not version == self.DISC_CACHE_VERSION:
                raise FileNotFoundException
        return object

        
    def find(self, file):
        """
        Search the cache for informations about that file. The functions
        returns that information. Because the information can be 'None',
        the function raises a FileNotFoundException if the cache has
        no or out-dated informations.
        """
        if factory.isurl(file):
            split  = factory.url_splitter(file)
            # this is a complete cd caching
            if split[0] == 'cd':
                device, mountpoint, filename, complete_filename = split[1:]
            else:
                raise FileNotFoundException

            dname = device
            key = '%s__%s' % (os.stat(complete_filename)[stat.ST_MTIME], filename)
            
        else:
            file  = os.path.abspath(file)

            if stat.S_ISBLK(os.stat(file)[stat.ST_MODE]):
                return self.__find_disc__(file)

            dname = os.path.dirname(file)
            key = '%s__%s' % (os.stat(file)[stat.ST_MTIME], file)

        cachefile = self.__get_filename__(dname)

        if not dname == self.current_dir:
            if not (cachefile and os.path.isfile(cachefile)):
                raise FileNotFoundException

            f = open(cachefile, 'r')
            (version, objects) = pickle.load(f)
            f.close()
            if not version == self.CACHE_VERSION:
                raise FileNotFoundException
            
            self.current_dir     = dname
            self.current_objects = objects

        try:
            return self.current_objects[key]
        except:
            raise FileNotFoundException

