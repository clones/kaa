# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# hal.py - dbus/hal based monitor
# -----------------------------------------------------------------------------
# $Id$
#
# http://people.freedesktop.org/~david/hal-spec/hal-spec.html#interface-manager
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006-2008 Dirk Meyer
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

__all__ = [ 'signals', 'Device', 'start' ]

import sys
import os
import time
import signal
import logging

import kaa
import kaa.metadata

# check for dbus and it's version
import dbus
if getattr(dbus, 'version', (0,0,0)) < (0,8,0):
    raise ImportError('dbus >= 0.8.0 not found')

# Set dbus to use gtk and adjust kaa to it. Right now python dbus
# only supports the glib mainloop and no generic one.
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

# hal needs dbus
kaa.gobject_set_threaded()

# kaa.beacon imports
from kaa.beacon.server.config import config

# get logging object
log = logging.getLogger('beacon.hal')

# HAL signals
signals = kaa.Signals('add', 'remove', 'changed', 'failed')

@kaa.threaded(kaa.MAINTHREAD)
def emit_signal(signal, *args):
    """
    Wrapper to emit the signal in the main thread.
    """
    return signals[signal].emit(*args)


class Device(object):
    """
    A device object
    FIXME: lock because dbus and mainthread use this object
    """
    def __init__(self, prop, bus):
        self.udi = prop['info.udi']
        self.prop = prop
        self._bus = bus

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @kaa.threaded(kaa.GOBJECT)
    def mount(self):
        """
        Mount the device.
        """
        if self.prop.get('volume.mount_point'):
            # already mounted
            return False
        if not self.prop.get('volume.fstype'):
            log.error('unknown filesystem type for %s', self.udi)
        obj = self._bus.get_object('org.freedesktop.Hal', self.udi)
        vol = dbus.Interface(obj, 'org.freedesktop.Hal.Device.Volume')
        vol.Mount('', self.prop.get('volume.fstype'), [])
        return True

    @kaa.threaded(kaa.GOBJECT)
    def eject(self):
        """
        Eject the device. This includes umounting and removing from
        the list. Devices that can't be ejected (USB sticks) are only
        umounted and removed from the list.
        """
        _device_remove(self.udi)
        obj = self._bus.get_object('org.freedesktop.Hal', self.udi)
        vol = dbus.Interface(obj, 'org.freedesktop.Hal.Device.Volume')
        vol.Unmount([])
        if self.prop.get('volume.is_disc'):
            vol.Eject([])

    def __getattr__(self, attr):
        """
        Return attribute based on the properties.
        """
        return getattr(self.prop, attr)


    # -------------------------------------------------------------------------
    # Callbacks called in the GOBJECT thread
    # -------------------------------------------------------------------------

    def _modified(self, num_changes, change_list):
        """
        Device was modified (mount, umount..)
        Called by dbus in GOBJECT thread
        """
        for c in change_list:
            if c[0] == 'volume.mount_point':
                obj = self._bus.get_object('org.freedesktop.Hal', self.udi)
                obj = dbus.Interface(obj, 'org.freedesktop.Hal.Device')
                obj.GetAllProperties(reply_handler=self._property_update,
                                     error_handler=log.error)


    def _property_update(self, prop):
        """
        Update internal property list and call signal.
        Called by dbus in GOBJECT thread
        """
        prop = dict(prop)
        prop['info.parent'] = self.prop.get('info.parent')
        emit_signal('changed', self, prop).wait()
        self.prop = prop



# -----------------------------------------------------------------------------
# Connection handling
#
# All functions below this point are called in the GOBJECT thread. The used
# global variables are only used by this functions, but they modify the device
# objects. This needs a lock.
# -----------------------------------------------------------------------------

_bus = None
_connection_timeout = 5

@kaa.threaded(kaa.GOBJECT)
def start():
    """
    Connect to DBUS and start to connect to HAL.
    """
    global _bus
    global _connection_timeout
    _connection_timeout -= 1
    try:
        if not _bus:
            _bus = dbus.SystemBus()
    except Exception, e:
        # unable to connect to dbus
        if not _connection_timeout:
            # give up
            emit_signal('failed', 'unable to connect to dbus')
            return False
        kaa.OneShotTimer(start).start(2)
        return False
    try:
        obj = _bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
    except Exception, e:
        # unable to connect to hal
        emit_signal('failed', 'hal not found on dbus')
        return False
    hal = dbus.Interface(obj, 'org.freedesktop.Hal.Manager')
    hal.GetAllDevices(reply_handler=_device_all, error_handler=log.error)
    hal.connect_to_signal('DeviceAdded', _device_new)
    hal.connect_to_signal('DeviceRemoved', _device_remove)
    return False


# -----------------------------------------------------------------------------
# Device handling
# -----------------------------------------------------------------------------

_devices = []
_blockdevices = {}

def _device_all(device_names):
    """
    HAL callback with the list of all known devices.
    Called by dbus in GOBJECT thread.
    """
    for name in device_names:
        obj = _bus.get_object("org.freedesktop.Hal", str(name))
        obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device",
                             reply_handler=kaa.Callback(_device_add, name),
                             error_handler=log.error)


def _device_new(udi):
    """
    HAL callback for a new device.
    Called by dbus in GOBJECT thread.
    """
    obj = _bus.get_object("org.freedesktop.Hal", udi)
    obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device",
                         reply_handler=kaa.Callback(_device_add, udi, True),
                         error_handler=log.error)


def _device_remove(udi):
    """
    HAL callback when a device is removed.
    Called by dbus in GOBJECT thread or by eject
    """
    if udi in _blockdevices:
        del _blockdevices[udi]
        return True
    for dev in _devices:
        if dev.udi == udi:
            break
    else:
        return True
    # this causes an error later (no such id). Well, there is no disc with
    # that id, but we need to unreg, right? FIXME by reading hal doc.
    sig = _bus.remove_signal_receiver
    sig(dev._modified, "PropertyModified", 'org.freedesktop.Hal.Device',
        "org.freedesktop.Hal", udi)
    _devices.remove(dev)
    # signal changes
    if isinstance(dev.prop.get('info.parent'), dict):
        emit_signal('remove', dev)


def _device_add(prop, udi, removable=False):
    """
    HAL callback for property list of a new device. If removable is set to
    False this functions tries to detect if it is removable or not.
    Called by dbus in GOBJECT thread.
    """
    prop = dict(prop)
    if not 'volume.mount_point' in prop:
        if 'linux.sysfs_path' in prop and 'block.device' in prop:
            _blockdevices[udi] = prop
            for dev in _devices:
                if dev.prop.get('info.parent') == udi:
                    dev.prop['info.parent'] = prop
                    emit_signal('add', dev)
        return

    if prop.get('block.device').startswith('/dev/mapper') or \
           (prop.get('block.device') and config.discs and \
            (prop.get('block.device')[:-1] in config.discs.split(' ') or \
             prop.get('block.device')[:-2] in config.discs.split(' '))):
        # fixed device set in config
        return

    if config.discs:
        # fixed drives are set so this is a removable
        removable = True

    if not prop.get('volume.is_disc') and not removable:
        # No disc and not already marked as removable.
        # Check if the device is removable
        try:
            fd = open(os.path.dirname(prop["linux.sysfs_path"]) + '/removable')
            rm = fd.read(1)
            fd.close()
            if rm != '1':
                # not removable
                return
        except (OSError, KeyError):
            # Error reading info. Either file not found, linux.sysfs_path_device
            # not in prop or no read permissions. So not removable in that case.
            return
    elif prop.get('volume.is_disc') and prop.get('block.device'):
        # Set nice beacon unique id for discs
        try:
            prop['volume.uuid'] = kaa.metadata.cdrom.status(prop.get('block.device'))[1]
        except Exception, e:
            log.exception('device checking')
            return

    dev = Device(prop, _bus)
    _devices.append(dev)
    sig = _bus.add_signal_receiver
    sig(dev._modified, "PropertyModified", 'org.freedesktop.Hal.Device',
        "org.freedesktop.Hal", prop['info.udi'])

    parent = _blockdevices.get(prop.get('info.parent'))
    if parent:
        prop['info.parent'] = parent
        # signal changes
        emit_signal('add', dev)


if __name__ == '__main__':      
    def changed(dev, prop):
        print 'changed', dev.get('info.parent')
        print prop.get('volume.mount_point')
        print
    def remove(dev):
        print 'lost', dev
    def new_device(dev):
        print kaa.is_mainthread()
        print dev.udi
        dev.mount()
        kaa.OneShotTimer(dev.eject).start(1)
    kaa.gobject_set_threaded()
    signals['add'].connect(new_device)
    signals['changed'].connect(changed)
    signals['remove'].connect(remove)
    start()
    kaa.main.run()
