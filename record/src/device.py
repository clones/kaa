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
import os
import logging
import os
import traceback
from types import *

# kaa imports
from kaa.notifier import OneShotTimer, SocketDispatcher, Timer

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
        self.adapter = device
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
            self._fdsplitter = FDSplitter( self.adapter + '/dvr0', FDSplitter.INPUT_TS )

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


    def get_bouquet_list(self):
        """
        Return bouquet list from C++ object.
        """
        return self._device.get_bouquet_list()




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

        # End Encoding at GOP Ending Call 0=StopNOW, 1=GOPwait
        self.GOP_END = 0

        # The IVTV encoder needs time to flush and return a closed GOP.
        # NOTE: Be careful how we impliment channel changes!  On the bright
        #       side we can change channels in IVTV without closing the stream.
        # Setting this to 0 for now but if GOP_END==1 we need to keep reading
        # after STREAMOFF is called.  I had _some_ success with this but IMO
        # the driver is still just too flaky :(
        self.stop_start_delay = 0

        # We can't even overlap recordings on the same channel because in order
        # to stop with a nice stream (closed GOP at the end) we must use the
        # STREAMOFF ioctl which will screw up the second recording.
        self.max_recordings = 1

        # Even though we can only do one recording at a time, track the 
        # recording id and chain id.
        self.recording_id = 0
        self.recid2chainid = {}


    def start_recording(self, channel, filter_chain):
        log.debug('start recording channel %s' % channel)

        if len(self.recid2chainid) >= self.max_recordings:
            log.error('IVTV can only record %d thing(s) at a time' % \
                      self.max_recordings)

        self.setchannel(str(channel))
        self.assert_settings()
        self.set_gop_end(self.GOP_END)

        if self._fdsplitter == None:
            self._fdsplitter = FDSplitter(self.devfd)

        self.recording_id += 1
        chain_id = self._fdsplitter.add_filter_chain(filter_chain._create())
        self.recid2chainid[self.recording_id] = chain_id

        return self.recording_id


    def stop_recording(self, id):
        log.debug('stop recording %s' % id)

        if self.GOP_END:
            try:
                self.stop_encoding()
            except:
                log.error('STREAMOFF failed')
 
        OneShotTimer(self.remove_splitter, id).start(self.stop_start_delay)


    def remove_splitter(self, id):
        log.debug('remove splitter %s' % id)

        # remove filter chain
        if not self.recid2chainid.has_key(id):
            log.error('recid %d not found' % id)
            return None

        self._fdsplitter.remove_filter_chain(self.recid2chainid[id])

        # remove id from map
        del self.recid2chainid[id]

        # check if last filter chain was removed
        if not self.recid2chainid:
            self._fdsplitter = None

        self.close()
        self.open()


