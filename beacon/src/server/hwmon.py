# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# hwmon.py - HardwareMonitor
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006-2009 Dirk Meyer
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
import kaa
import kaa.metadata

# kaa.beacon imports
from ..utils import get_title

# get logging object
log = logging.getLogger('beacon.hwmon')

# import the different hardware monitor modules
try:
    import hal
except ImportError, e:
    log.error(e)
    log.error('HAL support disabled')
    hal = None
try:
    import cdrom
except ImportError:
    log.error('Cdrom support disabled')
    cdrom = None

class HardwareMonitor(object):

    def __init__(self, handler, db, rootfs):
        log.info('start hardware monitor')
        self._db = db
        # handler == beacon.server.Controller
        self.handler = handler
        self.devices = {}
        self._update_device(rootfs)
        if hal:
            hal.signals['failed'].connect(self.__backend_hal_failure)
            self.__backend_start(hal)
        elif cdrom:
            self.__backend_start(cdrom)

    def __backend_start(self, service):
        service.signals['add'].connect(self.__backend_device_new)
        service.signals['remove'].connect(self.__backend_device_remove)
        service.signals['changed'].connect(self.__backend_device_changed)
        service.start()

    def __backend_hal_failure(self, reason):
        log.error(reason)
        if cdrom:
            self.__backend_start(cdrom)

    def __backend_device_new(self, dev):
        if dev.prop.get('volume.uuid'):
            dev.prop['beacon.id'] = str(dev.prop.get('volume.uuid'))
        else:
            error = 'impossible to find unique string for beacon.id'
            if dev.prop.get('block.device'):
                error = 'unable to mount %s' % dev.prop.get('block.device')
            log.error(error)
            return True
        self.devices[dev.get('beacon.id')] = dev
        self._update_device(dev.prop)

    def __backend_device_remove(self, dev):
        try:
            del self.devices[dev.get('beacon.id')]
        except KeyError:
            log.error('unable to find %s', dev.get('beacon.id'))
        beacon_id = dev.prop.get('beacon.id')
        log.info('remove device %s' % beacon_id)
        self.handler.media_removed(self._db.medialist.get_by_media_id(beacon_id))
        self._db.medialist.remove(beacon_id)

    def __backend_device_changed(self, dev, prop):
        prop['beacon.id'] = dev.prop.get('beacon.id')
        beacon_id = dev.prop.get('beacon.id')
        log.info('change device %s', beacon_id)
        self._update_device(prop)

    def get_backend_device(self, dev):
        if hasattr(dev, 'prop'):
            # media object
            return self.devices.get(dev.prop.get('beacon.id'))
        # raw device dict
        return self.devices.get(dev.get('beacon.id'))

    def mount(self, dev):
        backend = self.get_backend_device(dev)
        if backend:
            return backend.mount()

    def eject(self, dev):
        backend = self.get_backend_device(dev)
        if backend:
            backend.eject()

    @kaa.coroutine()
    def _update_device(self, dev):
        id = dev.get('beacon.id')
        if self._db.medialist.get_by_media_id(id):
            # already in db
            media = self._db.medialist.get_by_media_id(id)
            media._beacon_update(dev)
            self.handler.media_changed(media)
            return
        media = self._db.query_media(id)
        if not media:
            if not dev.get('volume.is_disc') == True:
                # fake scanning for other media than rom drives
                metadata = None
            else:
                backend = self.get_backend_device(dev)
                parse = kaa.ThreadCallback(kaa.metadata.parse)
                metadata = yield parse(dev.get('block.device'))
            yield self._add_device_to_db(metadata, dev)
        media = self._db.query_media(id)
        if media['content'] == 'file' and not dev.get('volume.mount_point'):
            # FIXME: mount only on request
            log.info('mount %s', dev.get('block.device'))
            self.mount(dev)
            return
        m = yield self._db.medialist.add(id, dev)
        # create overlay directory structure
        if not os.path.isdir(m.overlay):
            os.makedirs(m.overlay, 0700)
        for d in ('large', 'normal', 'fail/beacon'):
            dirname = os.path.join(m.thumbnails, d)
            if not os.path.isdir(dirname):
                os.makedirs(dirname, 0700)
        # FIXME: Yes, a disc is read only, but other media may also
        # be read only and the flag is not set.
        if dev.get('volume.is_disc'):
            dev['volume.read_only'] = True
        self.handler.media_changed(m)
        return

    @kaa.coroutine(policy=kaa.POLICY_SYNCHRONIZED)
    def _add_device_to_db(self, metadata, dev):
        while self._db.read_lock.is_locked():
            yield self._db.read_lock.yield_unlock()
        # FIXME: check if the device is still valid
        # FIXME: handle failed dvd detection
        id = dev.get('beacon.id')
        if dev.get('volume.is_disc') == True and metadata and \
               metadata.get('mime') in ('video/vcd', 'video/dvd'):
            # pass rom drive
            type = metadata['mime'][6:]
            log.info('detect %s as %s' % (id, type))
            mid = self._db.add_object("media", name=id, content=type)['id']
            # FIXME: better label
            vid = self._db.add_object(
                "video", name="", parent=('media', mid),
                title=unicode(get_title(metadata['label'])), media = mid)['id']
            for track in metadata.tracks:
                self._db.add_object(
                    'track_%s' % type, name='%02d' % track.trackno,
                    parent=('video', vid), media=mid,
                    chapters=track.chapters, length=track.length,
                    audio=[ x.convert() for x in track.audio ],
                    subtitles=[ x.convert() for x in track.subtitles ])
        elif dev.get('volume.disc.has_audio') and metadata:
            # Audio CD
            log.info('detect %s as audio cd' % id)
            mid = self._db.add_object("media", name=id, content='cdda')['id']
            # FIXME: better label
            aid = self._db.add_object(
                "audio", name='', title = metadata.get('title'),
                artist = metadata.get('artist'), parent=('media', mid),
                media = mid)['id']
            for track in metadata.tracks:
                self._db.add_object(
                    'track_cdda', name=str(track.trackno),
                    title=track.get('title'), artist=track.get('artist'),
                    parent=('audio', aid),
                    media=mid)
        else:
            log.info('detect %s as normal filesystem' % id)
            mid = self._db.add_object("media", name=id, content='file')['id']
            mtime = 0                   # FIXME: wrong for /
            if dev.get('block.device'):
                mtime = os.stat(dev.get('block.device'))[stat.ST_MTIME]
            dir = self._db.add_object(
                "dir", name="", parent=('media', mid), media=mid, mtime=mtime)
