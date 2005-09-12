# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# filter.py - Filter for the recording stream
# -----------------------------------------------------------------------------
# $Id$
#
# This file defines an interface to the filter chain needed for recordings.
# The C++ code of a recording will use this chain to transform and output
# the data. The C++ objects will be removed when a recording is stopped.
# To avoid memory leaks, this wrapper class only represend a filter, the real
# C++ object is created when needed.
#
# Never call the _create function directly. This will create C++ objects
# that won't be deleted if you do. The functions should only be called inside
# the chain to create the C++ objects.
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

# kaa.record imports
import _filter

# get logging object
log = logging.getLogger('record')

class Chain(list):
    """
    A filter chain. You can append a filter to a chain and pass it to the
    device for recording.
    """
    def __init__(self):
        list.__init__(self)
        self.vpid = 0
        self.apid = 0


    def set_pids(self, vpid, apid):
        """
        Set vidoe and audio pids for this chain. This is only needed for
        MPEG-TS streams because they can conatin more than one channel.
        """
        self.vpid = vpid
        self.apid = apid


    def _create(self):
        """
        Internal function to create a filter chain C++ object. Do not call this
        function from outside kaa.record.
        """
        log.debug('create filter chain')
        chain = _filter.Chain()
        chain.add_pid(self.vpid)
        chain.add_pid(self.apid)
        for filter in self:
            if isinstance(filter, Remux):
                filter.vpid = self.vpid
                filter.apid = self.apid
            chain.append(filter)
        return chain.get_chain()


class Remux(object):
    """
    Remux filter to remux a MPEG-TS to MPEG-PES.
    """
    def __init__(self):
        self.vpid = 0
        self.apid = 0


    def _create(self):
        """
        Internal function to create a filter C++ object. Do not call this
        function from outside kaa.record.
        """
        log.info('add filter Remux')
        return _filter.Remux(self.vpid, self.apid)


class Filewriter(object):
    """
    Filewriter filter to save a stream to a file. If chunksize is greater
    zero, the filter will start a new file every time the chunk size is
    reached.
    """
    def __init__(self, filename, chunksize=0):
        self.filename = filename
        self.chunksize = chunksize


    def _create(self):
        """
        Internal function to create a filter C++ object. Do not call this
        function from outside kaa.record.
        """
        log.info('add filter Filewriter::%s' % self.filename)
        return _filter.Filewriter(self.filename, self.chunksize)


class UDPSend(object):
    """
    UDPSend filter to send the data over LAN using UDP. The addr has to
    ip:port and supports both unicast and multicast.
    """
    def __init__(self, addr):
        self.addr = addr


    def _create(self):
        """
        Internal function to create a filter C++ object. Do not call this
        function from outside kaa.record.
        """
        log.info('add filter UDPSend::%s' % self.addr)
        return _filter.UDPSend(self.addr)
