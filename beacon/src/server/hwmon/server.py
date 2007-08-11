# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - hardware monitor
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
import sys
import logging

# kaa imports
import kaa.rpc
import kaa.notifier
import kaa.metadata

# import the different hardware monitor modules
# this server is going to use

try:
    import hal
except ImportError:
    hal = None

try:
    import cdrom
except ImportError:
    cdrom = None

# load server config
from kaa.beacon.server.config import config

# get logging object
log = logging.getLogger('beacon.hwmon')


class Server(object):

    def __init__(self, configfile):
        log.info('start hardware monitor')

        # load config
        config.set_filename(configfile)
        config.load()

        self.master = None
        self.rpc = None
        self.devices = {}
        self._ipc = kaa.rpc.Server('hwmon')
        self._ipc.signals['client_connected'].connect_once(self.client_connect)
        self._ipc.connect(self)
        if hal:
            hal.signals['failed'].connect(self._hal_failure)
            self._start_service(hal)
        elif cdrom:
            self._start_service(cdrom)


    def _start_service(self, service):
        service.signals['add'].connect(self._device_new)
        service.signals['remove'].connect(self._device_remove)
        service.signals['changed'].connect(self._device_changed)
        service.start()


    def _hal_failure(self, reason):
        log.error(reason)
        if cdrom:
            self._start_service(cdrom)


    # -------------------------------------------------------------------------
    # Client handling
    # -------------------------------------------------------------------------

    def client_connect(self, client):
        """
        Connect a new client to the server.
        """
        log.info('beacon <-> hwmon connected')
        self.master = client
        # exit when the main server dies
        client.signals['closed'].connect(sys.exit)


    # -------------------------------------------------------------------------
    # Device handling
    # -------------------------------------------------------------------------

    def _device_new(self, dev):
        if dev.prop.get('volume.uuid'):
            # FIMXE: make this make unique if possible
            dev.prop['beacon.id'] = str(dev.prop.get('volume.uuid'))
        else:
            error = 'impossible to find unique string for beacon.id'
            if dev.prop.get('block.device'):
                error = 'unable to mount %s' % dev.prop.get('block.device')
            log.error(error)
            return True

        # FIXME: add a nice title

        self.devices[dev.get('beacon.id')] = dev
        if not self.rpc:
            return True
        self.rpc('device.add', dev.prop)


    def _device_remove(self, dev):
        try:
            del self.devices[dev.get('beacon.id')]
        except KeyError:
            log.error('unable to find %s in %s' % \
                      (dev.get('beacon.id'), self.devices.keys()))
        if not self.rpc:
            return True
        self.rpc('device.remove', dev.prop.get('beacon.id'))


    def _device_changed(self, dev, prop):
        if not self.rpc:
            return True
        prop['beacon.id'] = dev.prop.get('beacon.id')
        self.rpc('device.changed', dev.prop.get('beacon.id'), prop)


    # -------------------------------------------------------------------------
    # External RPC API
    # -------------------------------------------------------------------------

    @kaa.rpc.expose('connect')
    def connect(self):
        self.rpc = self.master.rpc
        for dev in self.devices.values():
            self.rpc('device.add', dev.prop)


    @kaa.rpc.expose('device.scan')
    def scan(self, id):
        dev = self.devices.get(id)
        if not dev:
            return None
        # FIXME: we don't the scanning in a thread, this could block.
        # But it shouldn't matter, but check that.
        return kaa.metadata.parse(dev.get('block.device'))


    @kaa.rpc.expose('device.mount')
    def mount(self, id):
        dev = self.devices.get(id)
        if not dev:
            return None
        dev.mount()


    @kaa.rpc.expose('device.eject')
    def eject(self, id):
        dev = self.devices.get(id)
        if not dev:
            return None
        dev.eject()
