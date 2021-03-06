# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# cdrom.py - CDROM monitor not using HAL
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

__all__ = [ 'signals', 'Device', 'start', 'eject' ]

# python imports
import os
import re
import array
import struct
import copy
import logging

try:
    from CDROM import *
    # test if CDROM_DRIVE_STATUS is there
    # (for some strange reason, this is missing sometimes)
    CDROM_DRIVE_STATUS
except:
    if os.uname()[0] == 'FreeBSD':
        # FreeBSD ioctls - there is no CDROM.py...
        CDIOCEJECT = 0x20006318
        CDIOCCLOSE = 0x2000631c
        CDIOREADTOCENTRYS = 0xc0086305L
        CD_LBA_FORMAT = 1
        CD_MSF_FORMAT = 2
        CDS_NO_DISC = 1
        CDS_DISC_OK = 4
    else:
        # strange ioctls missing
        CDROMEJECT = 0x5309
        CDROMCLOSETRAY = 0x5319
        CDROM_DRIVE_STATUS = 0x5326
        CDROM_SELECT_SPEED = 0x5322
        CDS_NO_DISC = 1
        CDS_DISC_OK = 4

# kaa imports
import kaa
from kaa import Timer, MainThreadCallable
from kaa.ioctl import ioctl
import kaa.metadata

# get logging object
log = logging.getLogger('beacon.hal')

# signals
signals = kaa.Signals('add', 'remove', 'changed')

# list of detected drives
_rom_drives = []

CDROM_THREAD = 'beacon.cdrom'

def fstab():
    """
    Read /etc/fstab into a list of (device, mountpoint, type, options)
    """
    if not os.path.isfile('/etc/fstab'):
        return []
    result = []
    regexp = re.compile('([^ \t]*)[ \t]*([^ \t]*)[ \t]*([^ \t]*)[ \t]*([^ \t]*)')
    fd = open('/etc/fstab')
    for line in fd.readlines():
        if line.find('#') >= 0:
            line = line[:line.find('#')]
        line = line.strip()
        if not line:
            continue
        if not regexp.match(line):
            continue
        device, mountpoint, type, options = regexp.match(line).groups()
        device = os.path.realpath(device)
        result.append((device, mountpoint, type, options))
    fd.close()
    return result


@kaa.threaded(CDROM_THREAD)
def eject(device):
    # open fd to the drive
    try:
        fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
        # try to open the drive
        if os.uname()[0] == 'FreeBSD':
            s = ioctl(fd, CDIOCEJECT, 0)
        else:
            s = ioctl(fd, CDROMEJECT, 0)
    except (OSError, IOError), e:
        log.exception('eject error')
        return
    try:
        # close the fd to the drive
        os.close(fd)
    except (OSError, IOError), e:
        log.exception('close fd')



class Device(object):
    """
    ROM drive information
    """
    def __init__(self, prop):
        self.prop = prop
        self.udi = prop['info.udi']
        self._eject = False

    def mount(self, umount=False):
        """
        Mount the disc
        """
        if self.prop.get('volume.mount_point') and not umount:
            # already mounted
            return False
        cmd = ('mount', self.prop['block.device'])
        if umount:
            cmd = ('umount', self.prop['block.device'])
        proc = kaa.Process(cmd)
        proc.stdout.signals['readline'].connect(log.warning)
        proc.stderr.signals['readline'].connect(log.error)
        proc.start()
        return True

    def eject(self):
        """
        Eject the device. This includes umounting and removing from
        the list. Devices that can't be ejected (USB sticks) are only
        umounted and removed from the list.
        """
        if self.prop.get('volume.mount_point'):
            # umount before eject
            self._eject = True
            return self.mount(umount=True)
        eject(self.prop['block.device'])

    def _set_mountpoint(self, mountpoint=None):
        """
        Set mountpoint
        """
        prop = copy.copy(self.prop)
        if mountpoint:
            prop['volume.mount_point'] = mountpoint
        elif prop.get('volume.mount_point'):
            del prop['volume.mount_point']
        if not self._eject:
            signals['changed'].emit(self, prop)
        self.prop = prop
        if self._eject:
            eject(self.prop['block.device'])

    def __getattr__(self, attr):
        """
        Generic attribute getter
        """
        return getattr(self.prop, attr)


class RomDrive(object):
    """
    Monitor for ROM drives
    """
    def __init__(self, device, mountpoint, type, options):
        self.device = device
        self.mountpoint = mountpoint
        self.type = type
        self.options = options
        self.status = -1
        self.disc = None
        # call check every 2 seconds
        self.check_timer = Timer(self.check).start(1)

    @kaa.threaded(kaa.MAINTHREAD)
    def remove_disc(self):
        """
        Remove disc from the internal list
        """
        if not self.disc:
            return
        signals['remove'].emit(self.disc)
        self.disc = None

    @kaa.threaded(CDROM_THREAD)
    def check(self):
        log.debug('check drive status %s', self.device)
        # Check drive status
        try:
            fd = os.open(self.device, os.O_RDONLY | os.O_NONBLOCK)
        except (OSError, IOError), e:
            return
        try:
            if os.uname()[0] == 'FreeBSD':
                data = array.array('c', '\000'*4096)
                (address, length) = data.buffer_info()
                buf = struct.pack('BBHP', CD_MSF_FORMAT, 0,
                                  length, address)
                s = ioctl(fd, CDIOREADTOCENTRYS, buf)
                s = CDS_DISC_OK
            else:
                CDSL_CURRENT = ( (int ) ( ~ 0 >> 1 ) )
                s = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT)
        except (OSError, IOError), e:
            os.close(fd)
            return
        # close fd
        os.close(fd)
        if s == self.status and self.disc:
            # no change, check mountpoint status
            if self.disc and os.path.ismount(self.mountpoint) and not \
                   self.disc.prop.get('volume.mount_point'):
                # disc is mounted
                MainThreadCallable(self.disc._set_mountpoint)(self.mountpoint)
            if self.disc and not os.path.ismount(self.mountpoint) and \
                   self.disc.prop.get('volume.mount_point'):
                # disc is mounted
                MainThreadCallable(self.disc._set_mountpoint)()
            return
        # remember status
        self.status = s
        if s is not CDS_DISC_OK:
            # No disc in drive
            self.remove_disc()
            return
        type, id = kaa.metadata.cdrom.status(self.device)
        if not id:
            # bad disc, let us assume it is no disc
            self.remove_disc()
            return
        prop = { 'info.udi': id, 'volume.is_disc': True, 'volume.uuid': id, 'block.device': self.device }
        if os.path.ismount(self.mountpoint):
            prop['volume.mount_point'] = self.mountpoint
        # FIXME: make this vars in kaa.metadata
        if type in (1,4):
            prop['volume.disc.has_audio'] = True
        if type in (2,4):
            prop['volume.disc.has_data'] = True
        self.disc = Device(prop)
        MainThreadCallable(signals['add'].emit)(self.disc)


def start():
    """
    Start CDROM monitor
    """
    added = False
    for device, mountpoint, type, options in fstab():
        # fixme, add other stuff like supermount if people still use this
        if type == 'iso9660':
            _rom_drives.append(RomDrive(device, mountpoint, type, options))
            added = True
    if not added:
        log.info('CDROM monitor: no iso9660 filesystem in fstab found')
