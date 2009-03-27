# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# item.py - Beacon item
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006-2007 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

# python imports
import os
import logging

# kaa imports
import kaa

# kaa.beacon imports
from thumbnail import Thumbnail
from utils import get_title

# get logging object
log = logging.getLogger('beacon')

class Item(object):
    """
    A generic database item
    """

    def __init__(self, beacon_id, url, data, parent, media):
        # url of the item
        self.url = url
        self.filename = ''
        # internal data
        self._beacon_id = beacon_id
        # FIXME: ugly, maybe use the ObjectRow stuff from kaa.db
        # with extra write support. Or copy on write.
        self._beacon_data = dict(data)
        self._beacon_tmpdata = {}
        self._beacon_parent = parent
        self._beacon_media = media
        self._beacon_isdir = False
        self._beacon_changes = {}
        self._beacon_name = data['name']

    def get(self, key, default=None):
        """
        Access attributes of the item. If the attribute is not found
        the default value (None) will be returned.
        """
        if key.startswith('tmp:'):
            return self._beacon_tmpdata.get(key[4:], default)
        if key == 'parent':
            return self._beacon_parent
        if key == 'media':
            return self._beacon_media
        if key == 'read_only':
            # FIXME: this is not correct, a directory can also be
            # read only on a rw filesystem.
            return self._beacon_media.get('volume.read_only', default)
        if key in ('image', 'thumbnail'):
            image = self._beacon_data.get('image')
            if not image:
                if self._beacon_parent and self._beacon_id:
                    # This is not a good solution, maybe the parent is
                    # not up to date. Well, we have to live with that
                    # for now.  Only get image from parent if the item
                    # is scanned because it is a very bad idea that
                    # unscanned images (we do not know that they are
                    # images yet) inherit the image from a directory.
                    image = self._beacon_parent.get('image')
                if not image:
                    return default
            if image.startswith('http://'):
                fname = self._beacon_controller._db.md5url(image, 'images')
                if key == 'image':
                    if not os.path.isfile(fname):
                        # FIXME: We need to fetch the image. Right now this will not happen
                        # until beacon restarts or a thumbnail is requested
                        return default
                    return fname
                if key == 'thumbnail':
                    # the thumbnail code will take care of downloading
                    return Thumbnail(image, self._beacon_media)
            if key == 'image':
                return image
            if key == 'thumbnail':
                return Thumbnail(image, self._beacon_media)
        if key == 'title':
            t = self._beacon_data.get('title')
            if t:
                return t
            # generate some title and save local it for future use
            t = kaa.str_to_unicode(get_title(self._beacon_data['name'], self.isfile))
            self._beacon_data['title'] = t
            return t
        result = self._beacon_data.get(key, default)
        if result is None:
            return default
        return result

    def __getitem__(self, key):
        """
        Access attributes of the item. This function will never raise
        an exception. If the attribute is not found, None will be
        returned.
        """
        return self.get(key)

    def __setitem__(self, key, value):
        """
        Set the value of a given attribute. If the key starts with
        'tmp:', the data will only be valid in this item and not
        stored in the db.
        """
        if key.startswith('tmp:'):
            self._beacon_tmpdata[key[4:]] = value
            return
        self._beacon_data[key] = value
        if not self._beacon_changes:
            self._beacon_controller._beacon_update(self)
        self._beacon_changes[key] = value

    def keys(self):
        """
        List item attributes
        """
        return self._beacon_data.keys() + self._beacon_tmpdata.keys()

    def has_key(self, key):
        """
        Check if the item has a specific attribute set
        """
        return key in self._beacon_data.keys() or \
               key in self._beacon_tmpdata.keys()

    @property
    def scanned(self):
        """
        True if the item is in the database and fully scanned.
        """
        return self._beacon_id is not None

    @property
    def isdir(self):
        """
        True if the item is a directory.
        """
        return self._beacon_isdir

    @property
    def isfile(self):
        """
        True if the item is a regular file.
        """
        return not self._beacon_isdir and self.filename != ''

    @property
    def thumbnail(self):
        """
        Return a Thumbnail for the Item. See :ref:`thumbnail` for
        details about thumbnailing works in beacon.
        """
        return self.get('thumbnail')

    def list(self):
        """
        Return a Query object with all subitems of this item. If the
        client is not connected to the server an empty list will be
        returned instead.
        """
        # This function is not used internally
        if not self._beacon_id:
            result = kaa.InProgress()
            result.finish([])
            # FIXME: return empty Query object
            return result
        return self._beacon_controller.query(parent=self)

    def delete(self):
        """
        Delete item from the database (does not work on files)
        """
        return self._beacon_controller.delete_item(self)

    def scan(self):
        """
        Request the item to be scanned.
        """
        # Note: this function is not used by the server
        result = self._beacon_controller._beacon_parse(self)
        if isinstance(result, kaa.InProgress):
            result.connect_once(self._beacon_database_update)
        return result

    @property
    def ancestors(self):
        """
        Return an iterator to walk through the parents.
        """
        return ParentIterator(self)

    def _beacon_database_update(self, data):
        """
        Callback from db with new data
        """
        self._beacon_isdir = (data['type'] == 'dir')
        self._beacon_data = dict(data)
        self._beacon_id = (data['type'], data['id'])
        for key, value in self._beacon_changes.items():
            self._beacon_data[key] = value

    @property
    def _beacon_controller(self):
        """
        Get the controller (the client or the server)
        """
        return self._beacon_media._beacon_controller

    @property
    def _beacon_mtime(self):
        """
        Return modification time of the item itself.
        """
        return None

    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<beacon.Item %s>' % self.url


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
        self.item = self.item._beacon_parent
        return ret
