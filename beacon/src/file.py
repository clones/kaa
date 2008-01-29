# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# file.py - Beacon file item
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006-2008 Dirk Meyer
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

import kaa

# kaa.beacon imports
from item import Item

# get logging object
log = logging.getLogger('beacon')


class File(Item):
    """
    A file based database item.

    Attributes:
    url:         unique url of the item
    filename:    complete filename

    Functions:
    get:         get an attribute, optional argument force
    __getitem__: get an attribute
    __setitem__: set an attribute
    keys:        return all known attributes of the item
    scanned:     return True if the item is scanned
    list:        return list of subitems or directory content
    isdir:       return True if it is a directory
    isfile:      return True if it is a regular file

    Do not access attributes starting with _beacon outside kaa.beacon
    """

    def __init__(self, data, parent, overlay=False, isdir=False):
        if isinstance(data, str):
            # fake item, there is no database entry
            id = None
            filename = parent.filename + data
            data = { 'name': data }
            if parent and parent._beacon_id:
                data['parent_type'], data['parent_id'] = parent._beacon_id
            media = parent._beacon_media
            if isdir:
                filename += '/'
        elif isinstance(parent, File):
            # db data
            id = (data['type'], data['id'])
            media = parent._beacon_media
            filename = parent.filename + data['name']
            if isdir:
                filename += '/'
        elif not data['name']:
            # root directory
            id = (data['type'], data['id'])
            media = parent
            parent = None
            filename = media.mountpoint
        else:
            raise ValueError('unable to create File item from %s', data)

        Item.__init__(self, id, 'file://' + filename, data, parent, media)
        if self._beacon_data.get('scheme'):
            # file uses a special scheme like dvd
            self.url = self._beacon_data.get('scheme') + '://' + filename

        self._beacon_overlay = overlay
        self._beacon_isdir = isdir
        self._beacon_islink = False
        self.filename = filename
        if isdir:
            ovdir = filename[len(media.mountpoint):]
            self._beacon_ovdir = media.overlay + '/' + ovdir
            if os.path.islink(filename[:-1]):
                self._beacon_islink = True


    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def list(self, recursive=False):
        """
        Interface to kaa.beacon: List all files in the directory.
        """
        # This function is only used by the client
        if recursive:
            return self._beacon_controller().query(parent=self, recursive=True)
        return self._beacon_controller().query(parent=self)


    def scan(self):
        """
        Request the item to be scanned.
        Returns either False if not connected or an InProgress object.
        """
        # This function is only used by the client
        result = self._beacon_controller()._beacon_parse(self)
        if isinstance(result, kaa.InProgress):
            result.connect_once(self._beacon_database_update)
        return result


    def __repr__(self):
        """
        Convert object to string (usefull for debugging)
        """
        s = '<beacon.File %s' % self.filename
        if not self.url.startswith('file://'):
            s = '<beacon.File %s' % self.url
        if self._beacon_data.get('mtime') == None:
            s += ' (new)'
        else:
            s += ' (type=%s)' % str(self._beacon_data.get('type'))
        return s + '>'
