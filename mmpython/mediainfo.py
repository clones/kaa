#if 0
# $Id$
# $Log$
# Revision 1.4  2003/05/13 12:31:43  the_krow
# + Copyright Notice
#
#
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
TYPE_HYPERTEXT = 8

import string
import types

# Audiocore: TITLE, ARTIST, TRACKNO, TRACKOF, ALBUM, CHANNELS, SAMPLERATE, TYPE, SUBTYPE, LENGTH, ENCODER
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

def get_singleton():
    global _singleton

    # One-time init
    if _singleton == None:
        _singleton = SynchronizedObject(MetaDataFactory())
        print _singleton
        
    return _singleton

MEDIACORE = ['title', 'comment', 'artist', 'size', 'type', 'subtype', 'date', 'keywords', 'country', 'language']
AUDIOCORE = ['trackno', 'trackof', 'album', 'audiochannels', 'samplerate', 'length', 'encoder', 'audiocodec', 
             'samplebits', 'genre', 'audiobitrate']
VIDEOCORE = ['length', 'encoder', 'audiobitrate', 'audiochannels', 'bitrate', 'samplerate', 'audiocodec', 'videocodec', 'samplebits',
             'trackno', 'trackof', 'copyright', 'product', 'genre', 'secondary genre', 'subject', 'writer', 'producer', 
             'cinematographer', 'production designer', 'edited by', 'costume designer', 'music by', 'studio', 
             'distributed by', 'rating', 'starring', 'ripped by', 'digitizing date', 
             'internet address', 'source form', 'medium', 'source', 'archival location', 'commisioned by',
             'engineer', 'cropped', 'sharpness', 'dimensions', 'lightness', 'dots per inch', 'palette setting',
             'default audio stream', 'logo url', 'watermark url', 'info url', 'banner image', 'banner url', 
             'infotext', 'width', 'height',]
IMAGECORE = ['width','height','thumbnail','software','hardware']

class MediaInfo:
    def __init__(self):
        self.keys = []
        for k in MEDIACORE:
            setattr(self,k,None)
            self.keys.append(k)

    def setitem(self,item,dict,key):
        try:
            if self.__dict__.has_key(item):
                self.__dict__[item] = dict[key]
            else:
                print "Unknown key: %s" % item
        except:
            pass

    def __getitem__(self,key):
        return self.__dict__[key]

    def expand_keywords(self):
        resultset = []
        keywords = ()
        if isinstance(self.__dict__['keywords'],types.TupleType):
            print("tuple")
            keywords = self.__dict__['keywords']
        else:
            keywords = (self.__dict__['keywords'],)
        for i in keywords:
            if i:
                print("append: %s" % i)
                k = string.split( i, ',' ) 
                for it in k:
                    s = string.strip( it )
                    resultset.append( s )
        self.__dict__['keywords'] = tuple( resultset )
        
            

class AudioInfo(MediaInfo):
    def __init__(self):
        MediaInfo.__init__(self)
        for k in AUDIOCORE:
            setattr(self,k,None)
            self.keys.append(k)

class VideoInfo(MediaInfo):
    def __init__(self):
        MediaInfo.__init__(self)
        for k in VIDEOCORE:
            setattr(self,k,None)
            self.keys.append(k)
        self.languages = []

class ImageInfo(MediaInfo):
    def __init__(self):
        MediaInfo.__init__(self)
        for k in IMAGECORE:
            setattr(self,k,None)
            self.keys.append(k)
        
class MetaDataFactory:
    def __init__(self):
        self.extmap = {}
        self.types = []
        
    def create_from_file(self,file,filename=None):
        # Check extension as a hint
        for e in self.extmap.keys():
            if filename and filename.find(e) >= 0:
                t = self.extmap[e][3](file)
                if t.valid: return t
        print "No Type found by Extension. Trying all"
        for e in self.types:
            print "Trying %s" % e[1]
            t = e[3](file)
            if t.valid: return t
        return None

    def create_from_url(self,url):
        pass
        
    def create_from_filename(self,filename):
        f = open(filename,'rb')
        r = self.create_from_file(f,filename)
        f.close()
        return r
    
    def register(self,mimetype,extensions,type,c):
        tuple = (mimetype,extensions,type,c)
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
    import OggInfo
    t = _singleton.create_from_filename('7.ogg')
    print t