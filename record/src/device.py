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

# kaa imports
from kaa.notifier import SocketDispatcher, Timer

# kaa.record imports
from _dvb import DvbDevice as _DvbDevice
from ivtv_tuner import IVTV

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
        return self._device.start_recording(channel, filter_chain)


    def stop_recording(self, id):
        """
        Stop the recording with the given id.
        """
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
                 custom_frequencies=None, resolution=None, aspect=2,
                 audio_bitmask=None, bframes=None, bitrate_mode=1,
                 bitrate=4500000, bitrate_peak=4500000, dnr_mode=None,
                 dnr_spatial=None, dnr_temporal=None, dnr_type=None,
                 framerate=None, framespergop=None, gop_closure=1,
                 pulldown=None, stream_type=14):

        IVTV.__init__(self, device, norm, chanlist, card_input,
                      custom_frequencies, resolution, aspect,
                      audio_bitmask, bframes, bitrate_mode,
                      bitrate, bitrate_peak, dnr_mode, dnr_spatial,
                      dnr_temporal, dnr_type, framerate, framespergop,
                      gop_closure, pulldown, stream_type)


        # create socket dispatcher
        #sd = SocketDispatcher(self._device.read_fd_data)
        # give variable to the device
        #self._device.connect_to_notifier(sd)


    def start_recording(self, channel, filter_chain):
        log.info("start recording channel %s" % channel)
        self.assert_settings()
        self.set_gop_end()
        self.setchan(str(channel))


    def stop_recording(self, id):
        log.info("stop recording %s" % id)
        self.stop_encoding()
