__all__ = [ 'signals', 'Device', 'start', 'eject' ]

import os
import sys
import array
import struct
import fcntl
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

import kaa.notifier
from kaa.notifier import Timer, MainThreadCallback, Signal
from kaa.ioctl import ioctl
import kaa.metadata

from utils import fstab

# get logging object
log = logging.getLogger('beacon.hal')

# HAL signals
signals = { 'add': Signal(),
            'remove': Signal(),
            'changed': Signal(),
          }

_rom_drives = []

@kaa.notifier.execute_in_thread('beacon.cdrom')
def eject(device):
    # open fd to the drive
    try:
        fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
        # try to open the drive
        if os.uname()[0] == 'FreeBSD':
            s = ioctl(fd, CDIOCEJECT, 0)
        else:
            s = ioctl(fd, CDROMEJECT, 0)
    except Exception, e:
        log.exception('eject error')
    try:
        # close the fd to the drive
        os.close(fd)
    except:
        log.exception('close fd')

        

class Device(object):
    def __init__(self, prop):
        self.prop = prop
        self.udi = prop['info.udi']
        self._eject = False


    def mount(self, umount=False):
        if self.prop.get('volume.mount_point') and not umount:
            # already mounted
            return False
        cmd = ('mount', self.prop['block.device'])
        if umount:
            cmd = ('umount', self.prop['block.device'])
        proc = kaa.notifier.Process(cmd)
        proc.signals['stdout'].connect(log.warning)
        proc.signals['stderr'].connect(log.error)
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
        return getattr(self.prop, attr)

    
class RomDrive(object):
    def __init__(self, device, mountpoint, type, options):
        self.device = device
        self.mountpoint = mountpoint
        self.type = type
        self.options = options
        self.status = -1
        self.disc = None

        # call check every 2 seconds
        self.check_timer = Timer(self.check).start(1)


    def remove_disc(self):
        if not sef.disc:
            return
        MainThreadCallback(signals['remove'].emit)(self.disc)
        self.disc = None
        
        
    @kaa.notifier.execute_in_thread('beacon.cdrom')
    def check(self):
        log.debug('check drive status %s', self.device)

        # Check drive status
        try:
            fd = os.open(self.device, os.O_RDONLY | os.O_NONBLOCK)
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
        except Exception, e:
            # maybe we need to close the fd if ioctl fails, maybe
            # open fails and there is no fd
            try:
                os.close(fd)
            except (OSError, IOError):
                pass
            return

        # close fd
        os.close(fd)

        if s == self.status and self.disc:
            # no change, check mountpoint status
            if self.disc and os.path.ismount(self.mountpoint) and not \
                   self.disc.prop.get('volume.mount_point'):
                # disc is mounted
                MainThreadCallback(self.disc._set_mountpoint)(self.mountpoint)
            if self.disc and not os.path.ismount(self.mountpoint) and \
                   self.disc.prop.get('volume.mount_point'):
                # disc is mounted
                MainThreadCallback(self.disc._set_mountpoint)()
            return

        # remeber status
        self.status = s

        if s is not CDS_DISC_OK:
            # No disc in drive
            self.remove_disc()
            return

        id = kaa.metadata.getid(self.device)[1]
        if not id:
            # bad disc, let us assume it is no disc
            self.remove_disc()
            return

        prop = { 'info.udi': id,
                 'volume.is_disc': True,
                 'volume.uuid': id,
                 'block.device': self.device
               }
        if os.path.ismount(self.mountpoint):
            prop['volume.mount_point'] = self.mountpoint
        self.disc = Device(prop)
        MainThreadCallback(signals['add'].emit)(self.disc)



def start():
    for device, mountpoint, type, options in fstab():
        # fixme, add other stuff like supermount if people still use this
        if type == 'iso9660':
            _rom_drives.append(RomDrive(device, mountpoint, type, options))
