# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# fdsplitter.py - Devices for recordings
# -----------------------------------------------------------------------------
# $Id$
#
# This file defines the possible devices for recording.
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2005 Sönke Schwardt, Dirk Meyer
#
# First Edition: Sönke Schwardt <bulk@schwardtnet.de>
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
from _fdsplitter import FDSplitter as _FDSplitter

# get logging object
log = logging.getLogger('record')


class FDSplitter(object):
    """
    Reads data from file descriptor and passes it to registered filter chains.
    Based on the C++ module _FDSplitter.
    """
    def __init__(self, filedesc):
        """
        Init the device by creating a C++ object and create a
        SocketDispatcher for the file descriptor. The C++ objecty will
        register and unregister from notifier.
        """
        # create c++ object
        self._fdsplitter = _FDSplitter(filedesc);
        # create socket dispatcher
        sd = SocketDispatcher(self._fdsplitter.read_fd_data)
        # give variable to the device
        self._fdsplitter.connect_to_notifier(sd)


    def add_filter_chain(self, filter_chain):
        """
        Add filter chain ... bla bla bla ... TODO FIXME ...
        Start recording a channel to the filter chain. The filter chain needs
        the video and audio ids to know what part of the transport stream
        should be recorded. This functions gets all ids for the channel and
        starts the recording at C++ level.
        """
        return self._fdsplitter.add_filter_chain(filter_chain)


    def remove_filter_chain(self, id):
        """
        Stop the recording with the given id.
        """
        return self._fdsplitter.remove_filter_chain(id)
