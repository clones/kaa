# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# client.py - client part of the hardware monitor
# -----------------------------------------------------------------------------
# $Id$
#
# This module is used inside the beacon server to communicate with the
# hardware monitor process.
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
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
import os
import stat

# kaa imports
import kaa.rpc

# kaa.beacon imports
from kaa.beacon.media import medialist
from kaa.beacon.utils import get_title

# get logging object
log = logging.getLogger('beacon.hwmon')


class Client(object):

    def __init__(self):
        server = kaa.rpc.Client('hwmon')
        server.connect(self)
        self.rpc = server.rpc


    def set_database(self, handler, db, rootfs):
        self.db = db
        # handler == beacon.Server
        self.handler = handler
        medialist.connect(self.db, self)
        self.rpc('connect')
        self._device_add(rootfs)


    def mount(self, dev):
        if hasattr(dev, 'prop'):
            # media object
            id = dev.prop.get('beacon.id')
        else:
            # raw device dict
            id = dev.get('beacon.id')
        return self.rpc('device.mount', id)


    def eject(self, dev):
        return self.rpc('device.eject', dev.prop.get('beacon.id'))


    @kaa.rpc.expose('device.add')
    def _device_add(self, dev):
        # FIXME: check if the device is still valid

        id = dev.get('beacon.id')
        if medialist.get(id):
            # already in db
            media = medialist.get(id)
            media.update(dev)
            self.handler.media_changed(media)
            return

        media = self.db.query_media(id, None)[0]
        if not media:
            if not dev.get('volume.is_disc') == True:
                # fake scanning for other media than rom drives
                return self._device_scanned(None, dev)
            # scan the disc in background
            self.rpc('device.scan', id).connect(self._device_scanned, dev)
            return

        if media['content'] == 'file' and not dev.get('volume.mount_point'):
            # FIXME: mount only on request
            log.info('mount %s', dev.get('block.device'))
            self.mount(dev)
            return

        m = medialist.add(id, dev)

        # create overlay directory structure
        if not os.path.isdir(m.overlay):
            os.makedirs(m.overlay, 0700)
        for d in ('large', 'normal', 'fail/kaa'):
            dirname = os.path.join(m.thumbnails, d)
            if not os.path.isdir(dirname):
                os.makedirs(dirname, 0700)

        # FIXME: Yes, a disc is read only, but other media may also
        # be read only and the flag is not set.
        if dev.get('volume.is_disc'):
            dev['volume.read_only'] = True
        self.handler.media_changed(m)
        return


    @kaa.rpc.expose('device.remove')
    def _device_remove(self, id):
        log.info('remove device %s' % id)
        self.handler.media_removed(medialist.get(id))
        medialist.remove(id)


    @kaa.rpc.expose('device.changed')
    def _device_change(self, id, dev):
        log.info('change device %s', id)
        self._device_add(dev)


    def _device_scanned(self, metadata, dev):

        # FIXME: check if the device is still valid
        # FIXME: handle failed dvd detection
        id = dev.get('beacon.id')
        if dev.get('volume.is_disc') == True and metadata and \
               metadata.get('mime') in ('video/vcd', 'video/dvd'):
            # pass rom drive
            type = metadata['mime'][6:]
            log.info('detect %s as %s' % (id, type))
            mid = self.db.add_object("media", name=id, content=type,
                                     beacon_immediately=True)['id']
            # FIXME: better label
            vid = self.db.add_object("video",
                                     name="",
                                     parent=('media', mid),
                                     title=unicode(get_title(metadata['label'])),
                                     media = mid,
                                     beacon_immediately=True)['id']
            self.db.commit(force=True)
            for track in metadata.tracks:
                self.db.add_object('track_%s' % type, name='%02d' % track.trackno,
                                   parent=('video', vid), media=mid,
                                   mtime=0, chapters=track.chapters, length=track.length,
                                   audio=[ x.convert() for x in track.audio ],
                                   subtitles=[ x.convert() for x in track.subtitles ])
            self.db.commit()
        elif dev.get('volume.disc.has_audio') and metadata:
            # Audio CD
            log.info('detect %s as audio cd' % id)
            mid = self.db.add_object("media", name=id, content='cdda',
                                     beacon_immediately=True)['id']
            # FIXME: better label
            aid = self.db.add_object("audio",
                                     name='',
                                     title = metadata.get('title'),
                                     artist = metadata.get('artist'),
                                     parent=('media', mid),
                                     media = mid,
                                     beacon_immediately=True)['id']
            self.db.commit(force=True)
            for track in metadata.tracks:
                self.db.add_object('track_cdda', name=str(track.trackno),
                                   title=track.get('title'),
                                   artist=track.get('artist'),
                                   album=metadata.get('title'),
                                   parent=('audio', aid),
                                   media=mid,
                                   mtime=0)
            self.db.commit()

        else:
            log.info('detect %s as normal filesystem' % id)
            mid = self.db.add_object("media", name=id, content='file',
                                     beacon_immediately=True)['id']
            mtime = 0                   # FIXME: wrong for /
            if dev.get('block.device'):
                mtime = os.stat(dev.get('block.device'))[stat.ST_MTIME]
            dir = self.db.add_object("dir",
                                     name="",
                                     parent=('media', mid),
                                     media=mid, mtime=mtime,
                                     beacon_immediately=True)
            self.db.commit(force=True)
        self._device_add(dev)
