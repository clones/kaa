import os
import sys
import array
import struct
import fcntl

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

from kaa.notifier import ThreadCallback, OneShotTimer, MainThreadCallback
import kaa.metadata
from kaa.metadata.disc.discinfo import cdrom_disc_id

# kaa.vfs imports
import util

# get logging object
log = logging.getLogger('vfs')

def ioctl(fd, code, *args, **kargs):
    if code > sys.maxint:
        code = int(~(-code % sys.maxint) - 1)
    return fcntl.ioctl(fd, code, *args, **kargs)

class Device(object):
    def __init__(self, mountpoint, db, server):
        self.db = db
        self.mountpoint = mountpoint
        self.device = mountpoint.device
        self.server = server
        self.id = None
        self._callbacks = []
        self.check_timer = None

        
    def check(self):
        tcb = ThreadCallback(self.check_thread)
        tcb.signals['exception'].connect(log.error)
        tcb.register('vfs.cdrom')

        
    def check_thread(self):
        print 'check drive status'
        # Check drive status
        try:
            fd = os.open(self.device, os.O_RDONLY | os.O_NONBLOCK)
            if os.uname()[0] == 'FreeBSD':
                try:
                    data = array.array('c', '\000'*4096)
                    (address, length) = data.buffer_info()
                    buf = struct.pack('BBHP', CD_MSF_FORMAT, 0,
                                      length, address)
                    s = ioctl(fd, CDIOREADTOCENTRYS, buf)
                    s = CDS_DISC_OK
                except:
                    s = CDS_NO_DISC
            else:
                CDSL_CURRENT = ( (int ) ( ~ 0 >> 1 ) )
                s = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT)
        except Exception, e:
            # maybe we need to close the fd if ioctl fails, maybe
            # open fails and there is no fd
            try:
                os.close(fd)
            except:
                pass
            self.finished(None)
            return

        # Is there a disc present?
        if s != CDS_DISC_OK:
            os.close(fd)
            self.finished(None)
            return

        id  = cdrom_disc_id(self.device)[1]
        if not id:
            # bad disc, e.g. blank disc
            self.finished(None)
            return

        # close fd
        os.close(fd)

        # Do a db query in the main loop now
        MainThreadCallback(self.db_result, id)()


    def db_result(self, id):
        result = self.db.query(type="media", name=id)
        if result:
            self.finished(result[0]['name'])
            return
        tcb = ThreadCallback(kaa.metadata.parse, self.device)
        tcb.signals['exception'].connect(log.error)
        tcb.signals['completed'].connect(self.scan_result)
        tcb.register('vfs.cdrom')


    def scan_result(self, metadata):
        type = metadata['type'].lower()
        if 'track_%s' % type in self.db.object_types.keys():
            log.info('detected %s with tracks', type)
            type_list = self.db.object_types['track_%s' % type]
            disc = self.db.add_object("media", name=metadata.id, content=type,
                                      vfs_immediately = True)
            parent = ('media', disc['id'])
            for pos, track in enumerate(metadata.tracks):
                self.db.add_object('track_%s' % type, name = str(pos), parent = parent,
                                   media = disc['id'], metadata = track)
        else:
            # "normal" disc
            self.db.add_object("media", name=metadata.id, content='file')
        self.db.commit()
        self.finished(metadata.id)


    def finished(self, id):
        if self.server.set_mountpoint(self.mountpoint.directory, id):
            for callback in self._callbacks:
                if callback:
                    callback.update()
        self.check_timer.start(2)

        
    def monitor(self, callback):
        if self.id:
            callback.callback('checked')
        self._callbacks.append(callback)
        if not self.check_timer:
            self.check_timer = OneShotTimer(self.check)
            self.check_timer.start(0)
        
_devices = []

def monitor(device, callback, db, server):
    for d in _devices:
        if d.device == device:
            break
    else:
        for mountpoint in db.get_mountpoints(return_objects=True):
            if mountpoint.device == device:
                d = Device(mountpoint, db, server)
                _devices.append(d)
                break
        else:
            raise AttributeError('no such device')
    d.monitor(callback)
        
