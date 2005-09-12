# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# device.py - Devices for recordings
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
import logging

# kaa imports
from kaa.notifier import SocketDispatcher, Timer

# kaa.record imports
from _dvb import DvbDevice as _DvbDevice
from ivtv_tuner import IVTV

# get logging object
log = logging.getLogger('record')

class DvbDevice(object):
    """
    Wrapper for DVB devices.
    """
    def __init__(self, device, channels):
        self._device = _DvbDevice(device, channels);
        # create socket dispatcher
        sd = SocketDispatcher(self._device.read_fd_data)
        # give variable to the device
        self._device.connect_to_notifier(sd)


    def start_recording(self, channel, filter_chain):
        pids = self._device.get_pids(channel)
        log.info("start recording %s with pid list %s" % (channel, pids))
        filter_chain.set_pids(pids[0][0], pids[1][0])
        return self._device.start_recording(channel, filter_chain)
        
    def __getattr__(self, attr):
        if attr in ('get_card_type', 'get_bouquet_list',
                    'stop_recording'):
            return getattr(self._device, attr)
        return object.__getattr__(self, attr)


class IVTVDevice(IVTV):
    """
    Class for IVTV devices.
    I'm still contemplating weather to keep this object extending IVTV
    or to use a _device line DvbDevice.
    """
    def __init__(self, device, norm, chanlist=None, card_input=4,
                 custom_frequencies=None, resolution=None, aspect=2,
                 audio_bitmask=None, bframes=None, bitrate_mode=1,
                 bitrate=4500000, bitrate_peak=4500000, dnr_mode=None,
                 dnr_spatial=None, dnr_temporal=None, dnr_type=None, framerate=None,
                 framespergop=None, gop_closure=1, pulldown=None, stream_type=14):

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
        

    def stop_recording(self, channel):
        log.info("stop recording channel %s" % channel)
        self.stop_encoding()
        

