#if 0
# -----------------------------------------------------------------------
# cache.py - caching of mmpython objects
# -----------------------------------------------------------------------
# $Id$
#
# $Log$
# Revision 1.40  2004/01/03 17:44:04  dischi
# catch OSError in case the file is removed file scanning
#
# Revision 1.39  2003/12/31 16:37:56  dischi
# again: faster, but all cachefiles have to be rebuild
#
# Revision 1.38  2003/12/30 22:30:04  dischi
# more speed improvments
#
# Revision 1.37  2003/12/30 15:18:34  dischi
# o don't calc the cachefile for every file when caching a directory
# o use higher pickle for Python 2.3
# o make it possible to store the data in a directory structure instead
#   of md5 hashed files.
#
# Revision 1.36  2003/11/05 21:17:37  dischi
# do not cache directory on audio discs
#
# Revision 1.35  2003/09/14 13:50:42  dischi
# make it possible to scan extention based only
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
import sys

import mmpython
import factory

from disc.discinfo import cdrom_disc_status, cdrom_disc_id, DiscInfo
from disc.datainfo import DataDiscInfo

if float(sys.version[0:3]) < 2.3:
    PICKLE_PROTOCOL = 1
else:
    PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL

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
        self.current_objects    = {}
        self.current_cachefile  = None
        self.current_cachedir   = None
        self.CACHE_VERSION      = 1
        self.DISC_CACHE_VERSION = 1
        self.md5_cachedir       = 1


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
        if not os.path.isfile(file):
            if not os.path.exists(file):
                return None
            if stat.S_ISBLK(os.stat(file)[stat.ST_MODE]):
                id = cdrom_disc_id(file)[1]
                if not id:
                    return None
                if self.md5_cachedir:
                    return '%s/disc/%s' % (self.cachedir, id)
                else:
                    return '%s/disc/%s.mmpython' % (self.cachedir, id)

        if not self.md5_cachedir:
            directory = os.path.join(self.cachedir, file[1:])
            if not os.path.isdir(directory):
                try:
                    os.makedirs(directory)
                except IOError:
                    return  '%s/%s' % (self.cachedir, self.hexify(md5.new(file).digest()))
            return os.path.join(directory, 'mmpython')
        return  '%s/%s' % (self.cachedir, self.hexify(md5.new(file).digest()))
            

    def __get_cachefile_and_filelist__(self, directory):
        """
        return the cachefile and the filelist for this directory
        """
        if factory.isurl(directory):
            split  = factory.url_splitter(directory)
            # this is a cd caching, one file for the complete disc
            if split[0] == 'cd':
                device, mountpoint, filename, complete_filename = split[1:]
                cachefile = self.__get_filename__(device)
                files = []
                for file in os.listdir(os.path.join(mountpoint, filename)):
                    files.append('cd://%s:%s:%s' % (device, mountpoint,
                                                    os.path.join(filename, file)))
            else:
                return (None, None)
                
        else:
            if not os.path.exists(directory):
                return (None, None)

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
        if not factory.isurl(directory):
            directory = os.path.abspath(directory)
        cachefile, files = self.__get_cachefile_and_filelist__(directory)
        if not cachefile:
            return -1

        new = 0
        for file in files:
            try:
                info = self.find(file, cachefile=cachefile, dirname=directory)
            except (FileNotFoundException, OSError):
                new += 1
        return new
    
        

    def cache_dir(self, directory, uncachable_keys, callback, ext_only):
        """
        cache every file in the directory for future use
        """
        if not factory.isurl(directory):
            directory = os.path.abspath(directory)
        cachefile, files = self.__get_cachefile_and_filelist__(directory)

        if not cachefile:
            return {}

        if self.md5_cachedir and len(cachefile[cachefile.rfind('/'):]) < 16:
            return {}

        objects = {}
        for file in files:
            if factory.isurl(file):
                split = factory.url_splitter(file)
                if split[0] == 'cd':
                    device, mountpoint, filename, complete_filename = split[1:]
                    timestamp = os.stat(complete_filename)[stat.ST_MTIME]
                    key       = filename
                else:
                    continue
            else:
                if not os.path.exists(file):
                    continue
                timestamp = os.stat(file)[stat.ST_MTIME]
                key       = file

            try:
                info = self.find(file)
            except (FileNotFoundException, OSError):
                info = mmpython.Factory().create(file, ext_only=ext_only)
                if callback:
                    callback()
                    
            if info:
                for k in uncachable_keys:
                    if info.has_key(k):
                        del info[k]
                try:
                    del info._tables
                except:
                    pass
            objects[key] = (info, timestamp)


        if factory.isurl(directory) and factory.url_splitter(directory)[0] == 'cd' and \
               not isinstance(self.current_objects, DiscInfo):
            if mmpython.mediainfo.DEBUG:
                print 'cd: add old entries'
            for key in self.current_objects:
                if mmpython.mediainfo.DEBUG:
                    print key
                objects[key] = self.current_objects[key]
        try:
            if os.path.isfile(cachefile):
                os.unlink(cachefile)
            f = open(cachefile, 'w')
            pickle.dump((self.CACHE_VERSION, objects), f, PICKLE_PROTOCOL)
            f.close()
        except IOError:
            print 'unable to save to cachefile %s' % cachefile
        self.current_objects = objects
        return objects
    


    def cache_disc(self, info):
        """
        Adds the information 'info' about a disc into a special disc database
        """
        if not isinstance(info, DiscInfo):
            return 0

        if hasattr(info, 'no_caching'):
            return 0
        
        cachefile = '%s/disc/%s' % (self.cachedir, info.id)
        if not self.md5_cachedir:
            cachefile += '.mmpython'
        try:
            if os.path.isfile(cachefile):
                os.unlink(cachefile)
            f = open(cachefile, 'w')
            pickle.dump((self.DISC_CACHE_VERSION, info), f, PICKLE_PROTOCOL)
            f.close()
        except IOError:
            print 'unable to save to cachefile %s' % cachefile
        return 1

    

    def __find_disc__(self, device):
        """
        Search the cache for informations about the disc. Called from find()
        """
        disc_type, id = cdrom_disc_id(device)

        if disc_type == 0:
            return None
        
        cachefile = '%s/disc/%s' % (self.cachedir, id)
        if not self.md5_cachedir:
            cachefile += '.mmpython'
        if not os.path.isfile(cachefile):
            raise FileNotFoundException
        f = open(cachefile, 'r')
        try:
            (version, object) = pickle.load(f)
        except:
            f.close()
            raise FileNotFoundException
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

        
    def find(self, file, cachefile=None, dirname=''):
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

            dirname   = device
            timestamp = os.stat(complete_filename)[stat.ST_MTIME]
            key       = filename
            
        elif not dirname:
            if not file.startswith('/'):
                file = os.path.abspath(file)

            if not os.path.isfile(file):
                if not os.path.exists(file):
                    raise FileNotFoundException
            
                if stat.S_ISBLK(os.stat(file)[stat.ST_MODE]):
                    return self.__find_disc__(file)

            dirname   = os.path.dirname(file)
            timestamp = os.stat(file)[stat.ST_MTIME]
            key       = file

        else:
            timestamp = os.stat(file)[stat.ST_MTIME]
            key       = file

        if dirname != self.current_cachedir:
            if not cachefile:
                cachefile = self.__get_filename__(dirname)

            if not cachefile == self.current_cachefile:
                self.current_cachefile = cachefile
                self.current_objects   = {}
                self.current_cachedir  = dirname

                if not (cachefile and os.path.isfile(cachefile)):
                    raise FileNotFoundException

                f = open(cachefile, 'r')
                try:
                    (version, objects) = pickle.load(f)
                except:
                    f.close()
                    raise FileNotFoundException
                f.close()
                if not version == self.CACHE_VERSION:
                    raise FileNotFoundException

                self.current_objects = objects

        if isinstance(self.current_objects, DiscInfo):
            raise FileNotFoundException
        if self.current_objects.has_key(key):
            obj, t = self.current_objects[key]
            if t != timestamp:
                raise FileNotFoundException
            return obj
        else:
            raise FileNotFoundException

