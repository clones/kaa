#if 0
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# $Log$
# Revision 1.2  2003/07/01 08:24:09  the_krow
# bugfixes
#
# Revision 1.1  2003/06/30 13:17:18  the_krow
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

import mediainfo
import stat
import os
import urlparse

DEBUG = 1



def url_splitter(url):
    split = urlparse.urlsplit(url)
    if split[0] != 'cd':
        return split
    path       = split[2]
    device     = path[2:path[2:].find(':')+2]
    filename   = path[path.rfind(':')+1:]
    mountpoint = path[len(device)+3:len(path)-len(filename)-1]
    return (split[0], device, mountpoint, filename, '%s/%s' % (mountpoint, filename))


def isurl(url):
    return url.find('://') > 0

class Factory:
    """
    Abstract Factory for the creation of MediaInfo instances. The different Methods
    create MediaInfo objects by parsing the given medium. 
    """
    def __init__(self):
        self.extmap = {}
        self.mimemap = {}
        self.types = []
        self.device_types = []
        self.stream_types = []
        
    def create_from_file(self,file):
        """
        create based on the file stream 'file
        """
        # Check extension as a hint
        for e in self.extmap.keys():
            if DEBUG > 1: print "trying ext %s" % e
            if file.name.find(e) + len(e) == len(file.name):
                if DEBUG == 1: print "trying ext %s" % e
                file.seek(0,0)
                t = self.extmap[e][3](file)
                if t.valid: return t

        if DEBUG: print "No Type found by Extension. Trying all"
        for e in self.types:
            if DEBUG: print "Trying %s" % e[0]
            try:
                file.seek(0,0)
                t = e[3](file)
                if t.valid:
                    if DEBUG: print 'found'
                    return t
            except:
                if DEBUG:
                    traceback.print_exc()
        if DEBUG: print 'not found'
        return None


    def create_from_url(self,url):
        """
        Create information for urls. This includes file:// and cd://
        """
        split  = url_splitter(url)
        scheme = split[0]

        if scheme == 'file':
            (scheme, location, path, query, fragment) = split
            return self.create_from_filename(location+path)

        elif scheme == 'cd':
            r = self.create_from_filename(split[4])
            if r:
                r.url = url
            return r
        
        elif scheme == 'http':
            # Quick Hack for webradio support
            # We will need some more soffisticated and generic construction
            # method for this. Perhaps move file.open stuff into __init__
            # instead of doing it here...
            for e in self.stream_types:
                if DEBUG: print 'Trying %s' % e[0]
                t = e[3](url)
                if t.valid:
                    t.url = url
                    return t
            
        else:
            (scheme, location, path, query, fragment) = split
            uhandle = urllib.urlopen(url)
            mime = uhandle.info().gettype()
            print "Trying %s" % mime
            if self.mimemap.has_key(mime):
                t = self.mimemap[mime][3](file)
                if t.valid: return t
            # XXX Todo: Try other types
        pass


    def create_from_filename(self,filename):
        """
        Create information for the given filename
        """
        if os.path.isfile(filename):
            f = open(filename,'rb')
            r = self.create_from_file(f)
            f.close()
            if r:
                r.url = 'file://%s' % os.path.abspath(filename)
                return r
        return None
    

    def create_from_device(self,devicename):
        """
        Create information from the device. Currently only rom drives
        are supported.
        """
        for e in self.device_types:
            if DEBUG: print 'Trying %s' % e[0]
            t = e[3](devicename)
            if t.valid:
                t.url = 'file://%s' % os.path.abspath(devicename)
                return t
        return None
            

    def create(self, name):
        """
        Global 'create' function. This function calls the different
        'create_from_'-functions.
        """
        if isurl(name):
            return self.create_from_url(name)
        if stat.S_ISBLK(os.stat(name)[stat.ST_MODE]):
            return self.create_from_device(name)
        return self.create_from_filename(name)

        
    def register(self,mimetype,extensions,type,c):
        if DEBUG > 0: print "%s registered" % mimetype
        tuple = (mimetype,extensions,type,c)
        if extensions == mediainfo.EXTENSION_DEVICE:
            self.device_types.append(tuple)
        elif extensions == mediainfo.EXTENSION_STREAM:
            self.stream_types.append(tuple)
        else:
            self.types.append(tuple)
            for e in extensions:
                self.extmap[e] = tuple
            self.mimemap[mimetype] = tuple



