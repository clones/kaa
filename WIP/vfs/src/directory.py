# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# directory.py - Directory item of the VFS
# -----------------------------------------------------------------------------
# $Id: item.py 1273 2006-03-11 19:34:08Z dmeyer $
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

# kaa.vfs imports
from item import Item

UNKNOWN = -1

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


    def _vfs_request(self):
        self._vfs_database_update(self._vfs_db()._vfs_request(self.filename[:-1]))


    def listdir(self):
        if not self._vfs_id:
            # item is not in db, request information now
            self._vfs_request()
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
