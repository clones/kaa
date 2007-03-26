# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# bin - Gstreamer V4L source bin element
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-record - A recording module
# Copyright (C) 2007 Sönke Schwardt, Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file AUTHORS for a complete list of authors.
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

# gstreamer imports
import pygst
pygst.require('0.10')
import gst

from tuner import Tuner
from frequencies import CHANLIST

class V4Lsrc(gst.Bin):
    def __init__(self):
        gst.Bin.__init__(self, 'v4lsrcbin_%d')
        self._device = '/dev/video0'
        self._norm = 'NTSC'
        self._tuner = Tuner(self._device, self._norm)
        self._src = gst.element_factory_make('v4lsrc')
        self._src.set_property('device', self._device)
        self._queue = gst.element_factory_make('queue')
        self.add(self._src, self._queue)

        # FIXME: make this a property
        size = 'width=%s,height=%s' % (720, 576)
        caps = gst.structure_from_string('video/x-raw-yuv,%s' % size)
        self._src.link_pads_filtered('src', self._queue, 'sink', gst.Caps(caps))

        pad = self._queue.get_pad('src')
        self._ghost = gst.GhostPad(pad.get_name(), pad)
        self.add_pad(self._ghost)
        self._chanlist = None


    def set_property(self, prop, value):
        if prop == 'chanlist':
            if not value in CHANLIST:
                raise AttributeError('unknown chanlist %s' % value)
            self._chanlist = value
            return True
        if prop == 'frequency':
            return self._tuner.setfreq(value)
        if prop == 'channel':
            if not self._chanlist:
                raise AttributeError('chanlist not set')
            if not value in CHANLIST[self._chanlist]:
                raise AttributeError('unknown channel %s' % value)
            return self._tuner.setfreq(CHANLIST[self._chanlist][value])
        if prop == 'device':
            self._device = value
            self._tuner = Tuner(self._device, self._norm)
            return self._src.set_property('device', self._device)
        if prop == 'norm':
            if not value.upper() in ('NTSC', 'PAL'):
                raise AttributeError('unknown norm %s' % value)
            self._norm = value.upper()
            self._tuner = Tuner(self._device, self._norm)
            return self._src.set_property('device', self._device)
        raise AttributeError


    def get_request_pad(self, type):
        if type == 'video':
            return self._ghost
        raise AttributeError
