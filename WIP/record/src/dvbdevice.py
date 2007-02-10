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
import traceback
from types import *
import urllib
import pygst
pygst.require('0.10')
import gst

# kaa imports
from kaa.notifier import OneShotTimer, SocketDispatcher, Timer

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
          e.g. 2 for /dev/dvb/adapter0/*
          
        channelconffile is of type string and specifies the path to a
        channels.conf file that will be used for tuning.                
        """

        # save adapter TODO FIXME unneccessary?
        self.adapter = adapter
        # keep filename of config file TODO FIXME unneccessary?
        self.channelconffile = channelconffile
        # read adapter config file
        self.channelconfig = DVBChannelConfReader( channelconffile )
        #
 
#       DEFINIERE HIER EINE FILTER-QUEUE

        # create gstreamer dvbtuner object
        self._tuner = gst.element_factory_make("dvbtuner", "tuner")
        # enable debug output
        self._tuner.set_property('debug-output', True)
        # use adapter specified by adapternumber
        self._tuner.set_property('adapter', adapternumber)

        # get frontend type and some additional information
        frontendtype = tuner.get_property('frontendtype')
        log.info('dvb device %s: type=%s  name="%s"  hwdecoder=%s' %
                 (adapternumber, frontendlist[ frontendtype ], tuner.get_property('frontendname'),
                  tuner.get_property('hwdecoder')))


    def start_recording(self, channel, filter_chain):
        """
        Start recording a channel to the filter chain. The filter chain needs
        the video and audio ids to know what part of the transport stream
        should be recorded. This functions gets all ids for the channel and
        starts the recording at C++ level.
        """

#        AUFNAHME STARTEN
#        - TUNER AUF ENTSPRECHENDE FREQUENZ/CHANNEL SETZEN, WENN ER DORT NOCH NICHT IST
#        - FILTERQUEUE ANPASSEN ==> NEUEN FILTER IN DIE QUEUE EINHÄNGEN
#        - RECORDING-ID ZURÜCKGEBEN
#          (RECORDING-ID==FILTER-ID, WIRD BENÖTIGT, UM SPÄTER DEN FILTER MODIFIZIEREN ZU KÖNNEN)

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

#        AUFNAME STOPPEN
#        - FILTER RAUSSUCHEN UND ENTFERNEN
#        - DIE FILTERQUEUE UND DER TUNER WERDEN ERST DANN DEAKTIVIERT, WENN JEMAND DAS AKTUELLE OBJEKT WEGWIRFT
        
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

 #       EINE MULTIPLEX LISTE ZUSAMMENBAUEN UND ZURÜCKGEBEN
        
        return self._device.get_bouquet_list()

