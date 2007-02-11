# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# dvbdevice.py - dvb device for recordings
# -----------------------------------------------------------------------------
# $Id$
#
# This file defines a dvb device for recording.
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2007 Sönke Schwardt, Dirk Meyer
#
# First Edition: Sönke Schwardt <bulk@schwardtnet.de>
# Maintainer:    Sönke Schwardt <bulk@schwardtnet.de>
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

import pygst
pygst.require('0.10')
import gst

import dvbconfigreader

# get logging object
log = logging.getLogger('record')

DVBFrontendList = [ "QPSK (DVB-S)", "QAM (DVB-C)", "OFDM (DVB-T)", "ATSC" ]

class DvbDevice(Device):
    """
    Recorder for DVB devices based on the gstreamer module .
    """
    def __init__(self, adapter, channelconffile):
        """
        Init the device by creating a gstreamer tuner object for the dvb
        adapter specified by 'adapter'. Additionally a DVBChannelConfigReader
        instance will read the given channel config file 'channelconffile'.

        adapter is of type int and specifies the local dvb adapter:
          e.g. 2 for /dev/dvb/adapter2/*

        channelconffile is of type string and specifies the path to a
        channels.conf file that will be used for tuning.
        """

        # save adapter TODO FIXME unneccessary?
        self.adapter = adapter
        # keep filename of config file TODO FIXME unneccessary?
        self.channelconffile = channelconffile
        # read adapter config file
        self.channelconfig = DVBChannelConfReader( channelconffile )

        # create gstreamer dvbtuner object
        self._tuner = gst.element_factory_make("dvbtuner", "tuner")
        # enable debug output
        self._tuner.set_property('debug-output', True)
        # use adapter specified by adapternumber
        self._tuner.set_property('adapter', adapternumber)

        # get frontend type and some additional information
        frontendtype = tuner.get_property('frontendtype')
        log.info('dvb device %s: type=%s  name="%s"  hwdecoder=%s' %
                 (adapternumber, frontendlist[ frontendtype ],
                  tuner.get_property('frontendname'),
                  tuner.get_property('hwdecoder')))


    def start_recording(self, channel, filter_chain):
        """
        Start recording a channel to the filter chain. The filter chain needs
        the video and audio ids to know what part of the transport stream
        should be recorded. This functions gets all ids for the channel and
        starts the recording at C++ level.
        """
        # tune to channel if needed
        # create new tssplitter pad
        # return id
        pass


    def stop_recording(self, id):
        """
        Stop the recording with the given id.
        """

        # FIXME: get filter and remove
        pass


    def get_channel_list(self):
        """
        """
        pass
