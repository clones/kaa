#if 0
# -----------------------------------------------------------------------
# cache.py - caching of mmpython objects
# -----------------------------------------------------------------------
# $Id$
#
# $Log$
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

import mediainfo

from disc import DiscID
from fcntl import ioctl



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


    def __get_filename__(self, directory):
        """
        return the cache filename for that directory
        """
        return '%s/%s' % (self.cachedir, self.hexify(md5.new(directory).digest()))
    

    def check_cache(self, directory):
        """
        Return how many files in this directory are not in the cache. It's
        possible to guess how much time the update will need.
        """
        cachefile = self.__get_filename__(directory)
        if not cachefile:
            return -1

        new = 0
        for file in [ os.path.join(directory, dname) for dname in os.listdir(directory) ]:
            try:
                info = self.find(file)
            except FileNotFoundException:
                new += 1
        return new
    
        
    def cache_dir(self, directory, uncachable_keys):
        """
        cache every file in the directory for future use
        """
        cachefile = self.__get_filename__(directory)
        if not cachefile:
            return {}

        objects = {}
        for file in [ os.path.join(directory, dname) for dname in os.listdir(directory) ]:
            key  = '%s__%s' % (os.stat(file)[stat.ST_MTIME], file)
            try:
                info = self.find(file)
            except FileNotFoundException:
                info = mediainfo.get_singleton().create_from_filename(file)

            if info:
                for k in uncachable_keys:
                    if info.has_key(k):
                        info[k] = None
            objects[key] = info

        pickle.dump((self.CACHE_VERSION, objects), open(cachefile, 'w'))
        self.current_objects = objects
        return objects
    

    def cache_disc(self, info):
        """
        Adds the information 'info' about a disc into a special disc database
        """

        if not isinstance(info, mediainfo.DiscInfo):
            return 0

        cachefile = '%s/disc/%s' % (self.cachedir, info.id)
        pickle.dump((self.DISC_CACHE_VERSION, info), open(cachefile, 'w'))
        return 1

    

    def __find_disc__(self, device):
        """
        Search the cache for informations about the disc. Called from find()
        """
        CDROM_DRIVE_STATUS=0x5326
        CDSL_CURRENT=( (int ) ( ~ 0 >> 1 ) )
        CDROM_DISC_STATUS=0x5327
        CDS_AUDIO=100
        CDS_MIXED=105

        try:
            fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
            s = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT)
        except:
            try:
                os.close(fd)
            except:
                pass
            raise FileNotFoundException
        
        s = ioctl(fd, CDROM_DISC_STATUS)
        os.close(fd)
        if s == CDS_AUDIO or s == CDS_MIXED:
            disc_id = DiscID.disc_id(DiscID.open(device))
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
                id    = '%s_%s' % (id, m.group(1))
            else:
                id    = '%s_NO_LABEL' % id
            
        cachefile = '%s/disc/%s' % (self.cachedir, id)
        if not os.path.isfile(cachefile):
            raise FileNotFoundException
        (version, object) = pickle.load(open(cachefile, 'r'))
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
        file  = os.path.abspath(file)

        if stat.S_ISBLK(os.stat(file)[stat.ST_MODE]):
            return self.__find_disc__(file)

        dname = os.path.dirname(file)
        key = '%s__%s' % (os.stat(file)[stat.ST_MTIME], file)
        cachefile = self.__get_filename__(dname)

        if not dname == self.current_dir:
            if not (cachefile and os.path.isfile(cachefile)):
                raise FileNotFoundException

            (version, objects) = pickle.load(open(cachefile, 'r'))
            if not version == self.CACHE_VERSION:
                raise FileNotFoundException
            
            self.current_dir     = dname
            self.current_objects = objects

        if self.current_objects.has_key(key):
            return self.current_objects[key]

        raise FileNotFoundException

