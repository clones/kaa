# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# device.py - Devices for recordings
# -----------------------------------------------------------------------------
# $Id$
#
# This file defines the possible devices for recording.
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
import logging
import traceback
from types import *

# kaa imports
from kaa.notifier import SocketDispatcher, Timer

# kaa.record imports
from _dvb import DvbDevice as _DvbDevice
from ivtv_tuner import IVTV
from fdsplitter import FDSplitter

# get logging object
log = logging.getLogger('record')


class Device(object):
    """
    Basic device class defining the needed functions all devices need to
    provide. Override all the functions without calling this class.
    """
    def start_recording(self, channel, filter_chain):
        """
        Start recording the channel to the filter chain. This function needs
        to return a unique id for stopping the recording later.
        """
        raise RuntimeError('start_recording undefined')


    def stop_recording(self, id):
        """
        Stop the recording with the given id.
        """
        raise RuntimeError('stop_recording undefined')

      

class DvbDevice(Device):
    """
    Recorder for DVB devices based on the C++ module _DvbDevice.
    """
    def __init__(self, device, channels):
        """
        Init the device by creating a C++ object for DVB and create a
        SocketDispatcher for the file descriptor. The C++ objecty will
        register and unregister from notifier.
        """
        self._device = _DvbDevice(device, channels);
        self._fdsplitter = None
        self.recid2chainid = { }


    def start_recording(self, channel, filter_chain):
        """
        Start recording a channel to the filter chain. The filter chain needs
        the video and audio ids to know what part of the transport stream
        should be recorded. This functions gets all ids for the channel and
        starts the recording at C++ level.
        """
        pids = self._device.get_pids(channel)
        log.info("start recording %s with pid list %s" % (channel, pids))
        filter_chain.set_pids(pids[0][0], pids[1][0])

        # create real filter chain
        filter_chain = filter_chain._create()

        # start recording	
        rec_id = self._device.start_recording(channel, filter_chain)

        # create FDSplitter if not existing
        if self._fdsplitter == None:
            self._fdsplitter = FDSplitter( self._device.get_fd() )
            self._fdsplitter.set_input_type( FDSplitter.INPUT_TS )

        chain_id = self._fdsplitter.add_filter_chain( filter_chain )

        self.recid2chainid[ rec_id ] = chain_id

        return rec_id


    def stop_recording(self, id):
        """
        Stop the recording with the given id.
        """
        # remove filter chain
        if not self.recid2chainid.has_key(id):
            log.error("recid %d not found" % id)
            return None

        self._fdsplitter.remove_filter_chain( self.recid2chainid[id] )

        # remove id from map
        del self.recid2chainid[id]

        # check if last filter chain was removed
        if not self.recid2chainid:
            self._fdsplitter = None

        # stop recording
        return self._device.stop_recording(id)


    def get_fd(self):
        """
        Returns a file descriptor that is opened for reading from /dev/dvb/adapterX/dvr0.
        If -1 is returned, the device is not opened.
        """
        return self._device.get_fd()
    

    def __getattr__(self, attr):
        """
        Support get_card_type and get_bouquet_list by passing the call to
        the C++ object.
        """
        if attr in ('get_card_type', 'get_bouquet_list'):
            return getattr(self._device, attr)
        return object.__getattr__(self, attr)



class IVTVDevice(Device, IVTV):
    """
    Class for IVTV devices.
    I'm still contemplating weather to keep this object extending IVTV
    or to use a _device line DvbDevice.
    """
    def __init__(self, device, norm, chanlist=None, card_input=4,
                 custom_frequencies=None, resolution=None, aspect=None,
                 audio_bitmask=None, bframes=None, bitrate_mode=None,
                 bitrate=None, bitrate_peak=None, dnr_mode=None,
                 dnr_spatial=None, dnr_temporal=None, dnr_type=None,
                 framerate=None, framespergop=None, gop_closure=1,
                 pulldown=None, stream_type=None):

        IVTV.__init__(self, device, norm, chanlist, card_input,
                      custom_frequencies, resolution, aspect,
                      audio_bitmask, bframes, bitrate_mode,
                      bitrate, bitrate_peak, dnr_mode, dnr_spatial,
                      dnr_temporal, dnr_type, framerate, framespergop,
                      gop_closure, pulldown, stream_type)

        self._fdsplitter = None

        # For IVTV we have one device that we rely on for both the ioctl
        # commands and reading the data.  It may be beneficial to maintain
        # seperate file descriptors for the two operations.  I am trying
        # things both ways and will clean up the mess when satisfied.
        # self.read_file = None

        # I don't think recording_id means much for IVTV since we can only
        # record one channel per device.
        self.recording_id = 0

        self.recid2chainid = {}


    def start_recording(self, channel, filter_chain):
        log.info("start recording channel %s" % channel)

        # If we don't know the channel, return -1

        if self.get_fd() < 0:
            log.debug('read_file is closed, opening')
            if self.open() < 0:
                log.error('open failed')
                return -1

        self.setchannel(str(channel))
        self.assert_settings()
        self.set_gop_end()

        if self._fdsplitter == None:
            self._fdsplitter = FDSplitter(self.get_fd())

        self.recording_id += 1
        chain_id = self._fdsplitter.add_filter_chain(filter_chain._create())
        self.recid2chainid[self.recording_id] = chain_id

        return self.recording_id


    def stop_recording(self, id):
        log.info("stop recording %s" % id)

        # self.stop_encoding()

        # remove filter chain
        if not self.recid2chainid.has_key(id):
            log.error("recid %d not found" % id)
            return None

        self._fdsplitter.remove_filter_chain(self.recid2chainid[id])

        # remove id from map
        del self.recid2chainid[id]

        # check if last filter chain was removed
        if not self.recid2chainid:
            self._fdsplitter = None


    def get_fd(self):
        return self.devfd

# Thinking out loud.
#        if self.read_file is None:
#            return -1
#
#        try:
#            fd = self.read_file.fileno()
#        except:
#            log.error('get_fd(): closed file')
#            traceback.print_exc()
#            return -1
# 
#        log.debug('fd: %d' % fd)
#        return fd


#    def open(self):
#        return self.get_fd()
#        if type(self.read_file) is FileType:
#            log.error('file already open: %s' % self.read_file.name)
#            return self.get_fd()
#
#        try:
#            self.read_file = open(self.device, 'r')
#        except:
#            log.error('failed to open: %s' % self.device)
#            return -1
#
#        return self.get_fd()


#    def close(self):
#        IVTV.close(self)
#        #self.read_file.close()


