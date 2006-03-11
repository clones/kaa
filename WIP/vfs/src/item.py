# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# item.py - Item of the VFS
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: handle all the FIXME and TODO comments inside this file and
#       add docs for functions, variables and how to use this file
#
# -----------------------------------------------------------------------------
# kaa-vfs - A virtual filesystem with metadata
# Copyright (C) 2005 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
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
import stat

# kaa imports
import kaa.thumb2
from kaa.strutils import str_to_unicode

UNKNOWN = -1

class Item(object):
    """
    Object Attributes:
    url, getattr, setattr, keys

    Do not access attributes starting with _vfs outside kaa.vfs
    """
    def __init__(self, _vfs_id, url, data, parent, media):
        # url of the item
        self.url = url

        # internal data
        self._vfs_id = _vfs_id
        self._vfs_data = data
        self._vfs_parent = parent
        self._vfs_media = media
        self._vfs_isdir = False
        self._vfs_changes = []
        self._vfs_name = data['name']


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<vfs.Item %s>' % self.url


    def _vfs_database_update(self, data):
        # callback from db
        self._vfs_data = data
        self._vfs_id = (data['type'], data['id'])

        
    def _vfs_db(self):
        # get db
        return self._vfs_media.client

    def _vfs_mtime(self):
        # return mtime
        return 0

    def _vfs_changed(self):
        return self._vfs_mtime() != self._vfs_data['mtime']


    def _vfs_tree(self):
        return ParentIterator(self)

    
    def getattr(self, key):
        if key == 'thumbnail' and hasattr(self, 'filename'):
            return kaa.thumb2.Thumbnail(self.filename, url=self.url)

        if key == 'image':
            image = ''
            if self._vfs_data.has_key('image'):
                image = self._vfs_data['image']
            if not image and self._vfs_parent:
                # This is not a good solution, maybe the parent is not
                # up to date. Well, we have to live with that for now.
                return self._vfs_parent.getattr('image')
            return image

        if key == 'title':
            if self._vfs_data.has_key('title'):
                t = self._vfs_data['title']
                if t:
                    return t
            t = self._vfs_data['name']
            if t.find('.') > 0:
                t = t[:t.rfind('.')]
            return str_to_unicode(t)
        
        # FIXME: make sure we have db data
        if self._vfs_data.has_key(key):
            return self._vfs_data[key]
        return None


    def setattr(self, key, value):
        self._vfs_data[key] = value
        if not self._vfs_changes and self._vfs_id:
            # FIXME: how to update an item not in the db yet?
            self.db.update(self)
        if not key in self._vfs_changes:
            self._vfs_changes.append(key)
        
            
    def keys(self):
        return self._vfs_data.keys()


class ParentIterator(object):

    def __init__(self, item):
        self.item = item

    def __iter__(self):
        return self

    def next(self):
        if not self.item:
            raise StopIteration
        ret = self.item
        self.item = self.item._vfs_parent
        return ret

class Directory(Item):
    """
    A directory based item.
    Object Attributes:
    url, filename, getattr, setattr, keys, listdir

    Do not access attributes starting with _vfs outside kaa.vfs
    """
    def __init__(self, data, parent):
        # Notes: filename end with '/'
        if isinstance(data, str):
            # fake item, there is no database entry
            id = None
            self.filename = parent.filename + data + '/' 
            data = { 'name': data, 'mtime': UNKNOWN }
            if parent and parent._vfs_id:
                data['parent_type'], data['parent_id'] = parent._vfs_id
            media = parent._vfs_media
        elif isinstance(parent, Directory):
            # db data
            id = (data['type'], data['id'])
            media = parent._vfs_media
            self.filename = parent.filename + data['name'] + '/'
        else:
            # root directory
            id = (data['type'], data['id'])
            media = parent
            parent = None
            self.filename = media.directory

        Item.__init__(self, id, 'file://' + self.filename, data, parent, media)
        self._vfs_overlay = False
        self._vfs_isdir = True


    def listdir(self):
        if not self._vfs_id:
            # item is not in db, request information now
            self._vfs_database_update(self._vfs_db()._vfs_request(self.filename[:-1]))
        return self._vfs_db().query(parent=self)
        

    def _vfs_listdir(self):
        try:
            listdir = os.listdir(self.filename)
        except OSError:
            return []

        media = self._vfs_media
        overlay = media.overlay + '/' + self.filename[len(media.directory):]
        try:
            result = [ ( x, True ) for x in os.listdir(overlay) \
                       if not x.startswith('.') and not x in listdir ]
        except OSError:
            result = []
        result += [ ( x, False ) for x in listdir if not x.startswith('.') ]
        result.sort(lambda x,y: cmp(x[0], y[0]))
        return result


    def _vfs_os_listdir(self):
        if hasattr(self, '_vfs_os_listdir_cache'):
            return self._vfs_os_listdir_cache
        
        try:
            result = [ (x, self.filename + x) for x in os.listdir(self.filename)
                       if not x.startswith('.') ]
        except OSError:
            return []

        media = self._vfs_media
        overlay = media.overlay + '/' + self.filename[len(media.directory):]
        try:
            result += [ ( x, overlay + x ) for x in os.listdir(overlay) \
                        if not x.startswith('.') and not x in listdir ]
        except OSError:
            pass
        self._vfs_os_listdir_cache = result
        return result
        
    def _vfs_mtime(self):
        # TODO: add overlay dir to mtime
        return os.stat(self.filename)[stat.ST_MTIME]
    
        
    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        str = '<vfs.Directory %s' % self.filename
        if self._vfs_data['mtime'] == UNKNOWN:
            str += ' (new)'
        return str + '>'
    

class File(Item):
    """
    A file based item.
    Object Attributes:
    url, filename, getattr, setattr, keys

    Do not access attributes starting with _vfs outside kaa.vfs
    """
    def __init__(self, data, parent, overlay=False):
        if isinstance(data, str):
            # fake item, there is no database entry
            id = None
            self.filename = parent.filename + data
            data = { 'name': data, 'mtime': UNKNOWN }
            if parent and parent._vfs_id:
                data['parent_type'], data['parent_id'] = parent._vfs_id
            media = parent._vfs_media
        elif isinstance(parent, Directory):
            # db data
            id = (data['type'], data['id'])
            media = parent._vfs_media
            self.filename = parent.filename + data['name']

        Item.__init__(self, id, 'file://' + self.filename, data, parent, media)
        self._vfs_overlay = overlay


    def _vfs_mtime(self):
        # mtime is the the mtime for all files having the same
        # base. E.g. the mtime of foo.jpg is the sum of the
        # mtimeof foo.jpg and foo.jpg.xml or for foo.mp3 the
        # mtime is the sum of foo.mp3 and foo.jpg.
        search = self._vfs_data['name']
        if search.rfind('.') > 0:
            search = search[:search.rfind('.')]
        mtime = 0
        for basename, filename in self._vfs_parent._vfs_os_listdir():
            if basename.startswith(search):
                mtime += os.stat(filename)[stat.ST_MTIME]
        return mtime


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        str = '<vfs.File %s' % self.filename
        if self._vfs_data['mtime'] == UNKNOWN:
            str += ' (new)'
        return str + '>'


# make it possible to override these

