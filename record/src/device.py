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

# kaa imports
from kaa.notifier import SocketDispatcher, Timer

# kaa.record imports
from _dvb import DvbDevice as _DvbDevice

class DvbDevice(object):
    """
    Wrapper for DVB devices.
    """
    def __init__(self, device, channels, prio):
        self._device = _DvbDevice(device, channels, prio);
        # create socket dispatcher
        sd = SocketDispatcher(self._device.read_fd_data)
        # give variable to the device
        self._device.connect_to_notifier(sd)

    def start_recording(self, channel, filter_chain):
        pids = self._device.get_pids(channel)
        print pids
        filter_chain.set_pids(pids[0][0], pids[1][0])
        self._device.start_recording(channel, filter_chain)
        
    def __getattr__(self, attr):
        if attr in ('get_card_type', 'get_bouquet_list',
                    'stop_recording'):
            return getattr(self._device, attr)
        return object.__getattr__(self, attr)
