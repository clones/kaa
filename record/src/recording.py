# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# recording.py - Schedules recordings
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2005 Sönke Schwardt, Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/CREDITS for a complete list of authors.
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
import time
import logging

# kaa imports
from kaa.notifier import OneShotTimer, Signal

# get logging object
log = logging.getLogger('record')

class Recording(object):
    """
    Recording class to schedule a recording on a device.
    """

    # internal id counter
    NEXT_ID = 0

    def __init__(self, start, stop, device, channel, output):
        self.start = start
        self.stop = stop
        self.device = device
        self.channel = channel
        self.output = output
        self.id = Recording.NEXT_ID
        Recording.NEXT_ID += 1

        # signals to ge notified on changes
        self.signals = { 'start': Signal(), 'stop': Signal() }

        # internal timer
        self.timer = { 'start': OneShotTimer(self.__start),
                       'stop': OneShotTimer(self.__stop) }
        # id from device.start_recording
        self.__rec_id = None
        # start timer
        self.__schedule()
        
        
    def modify(self, start, stop):
        """
        Modify start or stop time of the recording. When the
        recording is running, changing the start time has no effect.
        """
        self.start = start
        self.stop = stop
        # restart timer
        self.__schedule()


    def remove(self):
        """
        Remove the recording.
        """
        if self.recording():
            self.__stop()
        self.timer['start'].stop()
        self.timer['stop'].stop()

        
    def recording(self):
        """
        Return True if the recording is in progress.
        """
        return self.__rec_id != None


    def active(self):
        """
        Return True if the recording is scheduled or in progress.
        """
        return self.timer['start'].active() or self.recording()


    def __schedule(self):
        """
        Schedule timer for recording.
        """
        if not self.recording():
            # rec not started yet
            wait = int(max(0, self.start - time.time()))
            log.info('start recording %s in %s seconds' % (self.id, wait))
            self.timer['start'].start(wait)
        wait = int(max(0, self.stop - time.time()))
        log.info('stop recording %s in %s seconds' % (self.id, wait))
        self.timer['stop'].start(wait)
            

    def __start(self):
        """
        Callback to start the recording.
        """
        log.info('start recording %s' % self.id)
        self.__rec_id = self.device.start_recording(self.channel, self.output)
        self.signals['start'].emit()

        
    def __stop(self):
        """
        Callback to stop the recording.
        """
        if not self.recording():
            # ignore, already dead
            log.info('recording %s already dead' % self.id)
            return
        log.info('stop recording %s' % self.id)
        self.device.stop_recording(self.__rec_id)
        self.__rec_id = None
        self.signals['stop'].emit()
