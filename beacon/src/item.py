# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# item.py - Beacon item
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
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
import kaa.notifier

# kaa.beacon imports
from thumbnail import Thumbnail
from hwmon.utils import get_title

# get logging object
log = logging.getLogger('beacon')

class Item(object):
    """
    A database item.

    Attributes:
    url:         unique url of the item
    filename:    empty string

    Functions:
    get:         get an attribute, optional argument force
    __getitem__: get an attribute
    __setitem__: set an attribute
    keys:        return all known attributes of the item
    scanned:     return True if the item is scanned
    list:        return list of subitems
    isdir:       return False
    isfile:      return False

    Do not access attributes starting with _beacon outside kaa.beacon
    """

    def __init__(self, _beacon_id, url, data, parent, media):
        # url of the item
        self.url = url
        self.filename = ''
        
        # internal data
        self._beacon_id = _beacon_id
        # FIXME: ugly, maybe use the ObjectRow stuff from kaa.db
        # with extra write support. Or copy on write.
        self._beacon_data = dict(data)
        self._beacon_tmpdata = {}
        self._beacon_parent = parent
        self._beacon_media = media
        self._beacon_isdir = False
        self._beacon_changes = {}
        self._beacon_name = data['name']


    # -------------------------------------------------------------------------
    # Public API for the client
    # -------------------------------------------------------------------------

    def get(self, key, request=False):
        """
        Interface to kaa.beacon. Return the value of a given attribute. If
        the attribute is not in the db, return None. If the key starts with
        'tmp:', the data will be fetched from a dict that is not stored in
        the db. Loosing the item object will remove that attribute. If
        request is True, scan the item if it is not in the db. If request is
        False and the item is not in the db, results will be very limited.
        When request is True this function may call kaa.notifier.step()
        """
        if key.startswith('tmp:'):
            return self._beacon_tmpdata.get(key[4:])

        if key == 'parent':
            return self._beacon_parent

        if key == 'media':
            return self._beacon_media

        if key in ('image', 'thumbnail'):
            image = ''
            if self._beacon_data.has_key('image'):
                image = self._beacon_data['image']
            if not image and self._beacon_parent:
                # This is not a good solution, maybe the parent is not
                # up to date. Well, we have to live with that for now.
                image = self._beacon_parent.get('image')
                if not image:
                    return None
            if key == 'image':
                return image

            if key == 'thumbnail':
                return Thumbnail(image, self._beacon_media)


        if key == 'title':
            t = self._beacon_data.get('title')
            if t:
                return t
            return str_to_unicode(get_title(self._beacon_data['name']))

        if request and not self._beacon_id:
            log.info('requesting data for %s', self)
            self._beacon_request()
            while not self._beacon_id:
                kaa.notifier.step()

        if self._beacon_data.has_key(key):
            return self._beacon_data[key]
        return None


    def __getitem__(self, key):
        return self.get(key)
    

    def __setitem__(self, key, value):
        """
        Interface to kaa.beacon. Set the value of a given attribute. If the key
        starts with 'tmp:', the data will only be valid in this item and not
        stored in the db. Loosing the item object will remove that attribute.
        """
        if key.startswith('tmp:'):
            self._beacon_tmpdata[key[4:]] = value
            return
        self._beacon_data[key] = value
        if not self._beacon_changes:
            self._beacon_controller()._beacon_update(self)
        self._beacon_changes[key] = value


    def keys(self):
        """
        Interface to kaa.beacon. Return all attributes of the item.
        """
        return self._beacon_data.keys() + self._beacon_tmpdata.keys()


    def has_key(self, key):
        """
        Returns True if the key is stored in the item.
        """
        return key in self._beacon_data.keys() or \
               key in self._beacon_tmpdata.keys()


    def scanned(self):
        """
        Return True if the item is in the database and fully scanned.
        """
        return self._beacon_id is not None


    def list(self):
        """
        Return all subitems to his item.
        """
        if not self._beacon_id:
            return []
        return self._beacon_controller().query(parent=self)


    def isdir(self):
        """
        Return if the item is a directory.
        """
        return self._beacon_isdir

    
    def isfile(self):
        """
        Return if the item is a regular file.
        """
        return not self._beacon_isdir and self.filename != ''

    
    # -------------------------------------------------------------------------
    # Internal API for client and server
    # -------------------------------------------------------------------------

    def _beacon_database_update(self, data, callback=None, *args, **kwargs):
        """
        Callback from db with new data
        """
        self._beacon_data = data
        self._beacon_id = (data['type'], data['id'])
        for key, value in self._beacon_changes.items():
            self._beacon_data[key] = value
        if callback:
            callback(*args, **kwargs)


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        return '<beacon.Item %s>' % self.url


    # -------------------------------------------------------------------------
    # Internal API for client
    # -------------------------------------------------------------------------

    def _beacon_controller(self):
        """
        Get the controller (the client or the server)
        """
        return self._beacon_media._beacon_controller()


    def _beacon_request(self):
        """
        Request the item to be scanned.
        """
        return None


    # -------------------------------------------------------------------------
    # Internal API for server
    # -------------------------------------------------------------------------

    def _beacon_mtime(self):
        """
        Return modification time of the item itself.
        """
        return None


    def _beacon_changed(self):
        """
        Return if the item is changed (based on modification time of
        the data and in the database).
        """
        return self._beacon_mtime() != self._beacon_data['mtime']


    def _beacon_tree(self):
        """
        Return an iterator to walk through the parents.
        """
        return ParentIterator(self)


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


def create_item(data, parent):
    url = parent.url
    if data['name']:
        if parent.url.endswith('/'):
            url = parent.url + data['name']
        else:
            url = parent.url + '/' + data['name']
    return Item((data['type'], data['id']), url, data, parent, parent._beacon_media)
