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
# Copyright (C) 2005,2008 Sönke Schwardt, Dirk Meyer
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
import os
import logging

# kaa imports
import kaa

# kaa.record imports
from _fdsplitter import FDSplitter as _FDSplitter

# get logging object
log = logging.getLogger('record')


class FDSplitter(object):
    """
    Reads data from file descriptor and passes it to registered filter chains.
    Based on the C++ module _FDSplitter.
    """
	
    INPUT_RAW = 0
    INPUT_TS  = 1	

    def __init__(self, filedesc, inputtype = INPUT_RAW):
        """
        Init the device by creating a C++ object and create a
        SocketDispatcher for the file descriptor. The C++ objecty will
        register and unregister from notifier.
        """
        # counter for added chains
        self.chains = 0
        if isinstance(filedesc, (str, unicode)):
            # filedesc is a filename, open the file and remember
            # to close it later
            self.fd = os.open(filedesc, os.O_RDONLY | os.O_NONBLOCK), True
        else:
            # filedesc is an already open file, remeber the fd
            # and do not close at the end.
            self.fd = filedesc, False

        # create c++ object
        self._fdsplitter = _FDSplitter( self.fd [ 0 ] );
        self._fdsplitter.set_input_type(inputtype)

        # create socket dispatcher
        self.sd = kaa.SocketDispatcher( self._fdsplitter.read_fd_data )


    def add_filter_chain(self, filter_chain):
        """
        Adds filter chain and returns id of that chain.
        """
        if self.chains == 0:
            self.sd.register( self.fd [ 0 ] )
        self.chains += 1
        return self._fdsplitter.add_filter_chain( filter_chain )


    def remove_filter_chain(self, id):
        """
        Stop the recording with the given id.
        """
        if self.chains == 1:
            self.sd.unregister()
        self.chains -= 1
        return self._fdsplitter.remove_filter_chain(id)


    def __del__(self):
        """
        Close file descriptor if it was opened by this object.
        """
        del self._fdsplitter
        if self.fd[ 1 ]:
            os.close( self.fd [ 0 ] )

