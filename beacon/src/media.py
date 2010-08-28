# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# media.py - Medialist handling
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

__all__ = [ 'MediaList' ]

# python imports
import os
import logging

# kaa imports
import kaa

# kaa.beacon imports
import utils

# get logging object
log = logging.getLogger('beacon')


class FakeMedia(object):
    """
    Media object for a media that is not available
    """
    def __init__(self, name):
        self.url = 'media://%s' % name

    @property
    def _beacon_media(self):
        """
        Get _beacon_media which is this object itself. To avoid circular
        references, use a property here.
        """
        return self

class Media(object):
    """
    Media object for a specific mount point.

    The following attributes are available.

     - C{name} (str, searchable | inverted_index: 'keywords')
     - C{content} (str, simple)

    @note: Objects are created by the hardware monitor subsystem, do not create
        Media objects from outside beacon.
    """
    def __init__(self, id, controller, beaconid=None):
        """
        Create a media object
        """
        self._beacon_controller = controller
        self.id = id
        # basic stuff
        self.label = id
        self.prop = {}
        self.device = None
        self.mountpoint = None
        self.beaconid = beaconid
        # needed by server.
        self.crawler = None

    def eject(self):
        """
        Eject the media.
        """
        self._beacon_controller.eject(self)

    @property
    def isdir(self):
        """
        Return False for items directly on the media without dir,
        like a dvd video.
        """
        return False

    def get(self, key, default=None):
        """
        Get value.
        """
        return self.prop.get(key, default)

    def __getitem__(self, key):
        """
        Get value
        """
        return self.prop[key]

    def __setitem__(self, key, value):
        """
        Set value
        """
        self.prop[key] = value

    def __repr__(self):
        """
        For debugging only.
        """
        return '<kaa.beacon.Media %s>' % self.id

    @kaa.coroutine()
    def _beacon_update(self, prop):
        """
        Update media properties.
        """
        self.prop = prop
        self.device = str(prop.get('block.device',''))
        self.mountpoint = str(prop.get('volume.mount_point',''))
        log.info('new media %s (%s) at %s', self.id, self.device, self.mountpoint)
        if not self.mountpoint:
            self.mountpoint = self.device
        if not self.mountpoint.endswith('/'):
            self.mountpoint += '/'
        # get basic information from database
        media = self._beacon_controller._beacon_media_information(self)
        if isinstance(media, kaa.InProgress):
            # This will happen for the client because in the client
            # _beacon_media_information needs to lock the db.
            media = yield media
        self.beaconid = media['id']
        prop['beacon.content'] = media['content']
        self._beacon_isdir = False
        if media['content'] == 'file':
            self._beacon_isdir = True
        self.thumbnails = os.path.join(self.overlay, '.thumbnails')
        if self.mountpoint == '/':
            self.thumbnails = os.path.join(os.environ['HOME'], '.thumbnails')
        if self.root.get('title'):
            self.label = self.root.get('title')
        elif prop.get('volume.label'):
            self.label = utils.get_title(prop.get('volume.label'))
        elif prop.get('info.parent'):
            self.label = u''
            parent = prop.get('info.parent')
            if parent.get('storage.vendor'):
                self.label += parent.get('storage.vendor') + u' '
            if parent.get('info.product'):
                self.label += parent.get('info.product')
            self.label.strip()
            if self.device:
                self.label += ' (%s)' % self.device
            if not self.label:
                self.label = self.id
        else:
            self.label = self.id

    @property
    def _beacon_media(self):
        """
        Get _beacon_media which is this object itself. To avoid circular
        references, use a property here.
        """
        return self


class MediaList(object):
    """
    List of current known Media objects.
    """
    def __init__(self):
        self._dict = {}
        self._idlist = []
        self._beacon_controller = None


    def connect(self, controller):
        """
        Connect a controller to the medialist.
        """
        for media in self._dict.keys():
            self.remove(media)
        self._beacon_controller = controller


    @kaa.coroutine()
    def add(self, id, prop):
        """
        Add a media.
        """
        if not self._beacon_controller:
            raise RuntimeError('not connected to database')
        if id in self._dict:
            yield self._dict.get(id)
        media = Media(id, self._beacon_controller)
        yield media._beacon_update(prop)
        self._dict[id] = media
        self._idlist = [ m._beacon_id[1] for m in self._dict.values() ]
        yield media


    def remove(self, id):
        """
        Remove a media
        """
        if not id in self._dict:
            log.error('%s not in list' % id)
            return None
        log.info('media %s removed from the list', id)
        media = self._dict.pop(id)
        self._idlist = [ m._beacon_id[1] for m in self._dict.values() ]
        return media


    def get_by_media_id(self, id):
        """
        Get media object by media id. If the id is not found return None.
        """
        return self._dict.get(id)


    def get_by_beacon_id(self, id):
        """
        Get media object by beacon id. If the id is not found return None.
        """
        for m in self._dict.values():
            if m._beacon_id == id:
                return m
        return None


    def get_by_directory(self, dirname):
        """
        Get media for the current directory. If the current directory
        is on no media return None (this should never happen)
        """
        if not dirname.endswith('/'):
            dirname += '/'
        # Sort from longest to shortest (most specific path appears first).
        all = sorted(self._dict.values(), key=lambda item: len(item.mountpoint), reverse=True)
        for m in all:
            if dirname.startswith(m.mountpoint):
                return m
        return None


    def get_all_beacon_ids(self):
        """
        Return a list of beacon ids for all mounted media.
        """
        return self._idlist


    def __iter__(self):
        """
        Iterate over all media objects.
        """
        return self._dict.values().__iter__()
