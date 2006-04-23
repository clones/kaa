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

from kaa.notifier import Timer, execute_in_thread, execute_in_mainloop, \
     MainThreadCallback, Signal
from kaa.base.ioctl import ioctl
import kaa.metadata

# get logging object
log = logging.getLogger('beacon.cdrom')

class Device(object):
    def __init__(self, mountpoint, db):
        self.db = db
        self.mountpoint = mountpoint
        self.device = mountpoint.device
        self.status = -1
        self.signals = { 'changed': Signal() }

        # call check every 2 seconds
        self.check_timer = Timer(self.check).start(2)

    @execute_in_thread('beacon.cdrom')
    def check(self):
        log.info('check drive status %s', self.device)
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
            s = CDS_NO_DISC

        if s == self.status:
            # no change
            return

        # remeber status
        self.status = s

        if s is not CDS_DISC_OK:
            # No disc in drive
            os.close(fd)
            MainThreadCallback(self.signals['changed'].emit)('')
            return

        id = kaa.metadata.getid(self.device)[1]
        if not id:
            # bad disc, let us assume it is no disc
            MainThreadCallback(self.signals['changed'].emit)('')
            return

        # close fd
        os.close(fd)

        if self.known_disc(id):
            # already in database, we are done here
            MainThreadCallback(self.signals['changed'].emit)(id)
            return

        log.info('scan disc for metadata')
        self.add(id, kaa.metadata.parse(self.device))
        MainThreadCallback(self.signals['changed'].emit)(id)

        
    @execute_in_mainloop()
    def known_disc(self, id):
        """
        Return something 'True' when the id is in the database.
        """
        return self.db.query(type="media", name=id)


    @execute_in_mainloop()
    def add(self, id, metadata):
        """
        Add id + metadata into the database.
        """
        type = metadata['type'].lower()
        if not 'track_%s' % type in self.db.object_types().keys() or \
               type == 'cd' and metadata['subtype'] == 'data':
            # "normal" disc
            log.info('detected normal disc')
            self.db.add_object("media", name=id, content='file')
            self.db.commit()
            return
        log.info('detected %s with tracks', type)
        disc = self.db.add_object("media", name=id, content=type,
                                  beacon_immediately = True)
        parent = ('media', disc['id'])
        for pos, track in enumerate(metadata.tracks):
            self.db.add_object('track_%s' % type, name = str(pos), parent = parent,
                               media = disc['id'], metadata = track)
        self.db.commit()
