#if 0
# -----------------------------------------------------------------------
# cache.py - caching of mmpython objects
# -----------------------------------------------------------------------
# $Id$
#
# $Log$
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
    def __init__(self, cachedir):
        self.cachedir = cachedir

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
    
    
    def cache_dir(self, directory):
        """
        cache every file in the directory for future use
        """
        cachefile = self.__get_filename__(directory)
        if not cachefile:
            return 0

        objects = {}
        for file in [ os.path.join(directory, dname) for dname in os.listdir(directory) ]:
            objects['%s__%s' % (os.stat(file)[stat.ST_MTIME], file)] = \
                             mediainfo.get_singleton().create_from_filename(file)

        pickle.dump((self.CACHE_VERSION, objects), open(cachefile, 'w'))
        return 1
    

    def cache_disc(self, info):
        """
        Adds the information 'info' about a disc into a special disc database
        """
        cachefile = '%s/disc' % self.cachedir
        if not self.current_dir == 'disc':
            if os.path.isfile(cachefile):
                (version, objects) = pickle.load(open(cachefile, 'r'))
                if not version == self.DISC_CACHE_VERSION:
                    print 'WARNING: disc cache changed, clearing cache'
                    self.current_objects = {}
                else:
                    self.current_objects = objects
            else:
                self.current_objects = {}

        if hasattr(info, 'id') and hasattr(info, 'label'):
            key = '%s_%s' % (info.id, info.label)
        elif hasattr(info, 'disc_id'):
            key = '%s %d ' % (info.disc_id, len(info.tracks))
            print '.%s.' % key
        else:
            print 'can\'t add object to cache, it has no id'
            return 0

        self.current_objects[key] = info
        pickle.dump((self.DISC_CACHE_VERSION, self.current_objects), open(cachefile, 'w'))
        return 1

    
    def find(self, file):
        """
        Search the cache for informations about that file. The functions
        returns that information. Because the information can be 'None',
        the function raises a FileNotFoundException if the cache has
        no or out-dated informations.
        """
        file  = os.path.abspath(file)

        if stat.S_ISBLK(os.stat(file)[stat.ST_MODE]):
            dname = 'disc'
            cachefile = '%s/disc' % self.cachedir

            CDROM_DRIVE_STATUS=0x5326
            CDSL_CURRENT=( (int ) ( ~ 0 >> 1 ) )
            CDROM_DISC_STATUS=0x5327
            CDS_AUDIO=100
            CDS_MIXED=105

            try:
                fd = os.open(file, os.O_RDONLY | os.O_NONBLOCK)
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
                id = DiscID.disc_id(DiscID.open(file))
                key = '%08lx %d ' % (id[0], id[1])

            else:
                f = open(file,'rb')

                f.seek(0x0000832d)
                id = f.read(16)
                f.seek(32808, 0)
                label = f.read(32)
                f.close()
                
                m = re.match("^(.*[^ ]) *$", label)
                if m:
                    label = m.group(1)
                else:
                    label = ''
                
                key = '%s_%s' % (id, label)
            
        else:
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

