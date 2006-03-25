# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# item.py - Item of the VFS
# -----------------------------------------------------------------------------
# $Id$
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
import logging

# kaa imports
from kaa.strutils import str_to_unicode

# kaa.vfs imports
from thumbnail import Thumbnail

# get logging object
log = logging.getLogger('vfs')

class Item(object):
    """
    A database item.

    Attributes:
    url:      unique url of the item
    getattr:  function to get an attribute
    setattr:  function to set an attribute
    keys:     function to return all known attributes of the item

    Do not access attributes starting with _vfs outside kaa.vfs
    """
    def __init__(self, _vfs_id, url, data, parent, media):
        # url of the item
        self.url = url

        # internal data
        self._vfs_id = _vfs_id
        self._vfs_data = data
        self._vfs_tmpdata = {}
        self._vfs_parent = parent
        self._vfs_media = media
        self._vfs_isdir = False
        self._vfs_changes = {}
        self._vfs_name = data['name']


    def _vfs_database_update(self, data):
        """
        Callback from db with new data
        """
        self._vfs_data = data
        self._vfs_id = (data['type'], data['id'])
        for key, value in self._vfs_changes.items():
            self._vfs_data[key] = value


    def _vfs_db(self):
        """
        Get the database connection (the client)
        """
        return self._vfs_media.client


    def _vfs_mtime(self):
        """
        Return modification time of the item itself.
        """
        return 0


    def _vfs_changed(self):
        """
        Return if the item is changed (based on modification time of
        the data and in the database).
        """
        return self._vfs_mtime() != self._vfs_data['mtime']


    def _vfs_request(self):
        """
        Request the item to be scanned.
        """
        pass


    def _vfs_tree(self):
        """
        Return an iterator to walk through the parents.
        """
        return ParentIterator(self)


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<vfs.Item %s>' % self.url


    def getattr(self, key, request=True):
        """
        Interface to kaa.vfs. Return the value of a given attribute. If
        the attribute is not in the db, return None. If the key starts with
        'tmp:', the data will be fetched from a dict that is not stored in
        the db. Loosing the item object will remove that attribute. If
        request is True, scan the item if it is not in the db. If request is
        False and the item is not in the db, results will be very limited.
        """
        if key.startswith('tmp:'):
            return self._vfs_tmpdata[key[4:]]

        if key == 'parent':
            return self._vfs_parent

        if key == 'thumbnail' and hasattr(self, 'filename'):
            return Thumbnail(self.filename, url=self.url)

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

        if request and not self._vfs_id:
            log.info('requesting data for %s', self)
            self._vfs_request()

        if self._vfs_data.has_key(key):
            return self._vfs_data[key]
        return None


    def setattr(self, key, value, request=True):
        """
        Interface to kaa.vfs. Set the value of a given attribute. If the key
        starts with 'tmp:', the data will only be valid in this item and not
        stored in the db. Loosing the item object will remove that attribute. If
        request is True, scan the item if it is not in the db. If request is
        False and the item is not in the db, the value may be lost.
        """
        if key.startswith('tmp:'):
            self._vfs_tmpdata[key[4:]] = value
            return
        if not self._vfs_id:
            log.info('requesting data for %s', self)
            self._vfs_request()
        self._vfs_data[key] = value
        if not self._vfs_changes and self._vfs_id:
            self._vfs_db().update(self)
        self._vfs_changes[key] = value


    def keys(self):
        """
        Interface to kaa.vfs. Return all attributes of the item.
        """
        return self._vfs_data.keys() + self._vfs_tmpdata.keys()


class ParentIterator(object):
    """
    Iterator to iterate thru the parent structure.
    """
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
