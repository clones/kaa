# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# gstreamer/child.py - child process for gstreamer backend
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.popcorn - Generic Player API
# Copyright (C) 2006 Jason Tackaberry, Dirk Meyer
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

# python imports
import os
import sys
import fcntl

# gstreamer imports
import pygst
pygst.require('0.10')
import gst

# import kaa.notifier and set mainloop to glib
import kaa.notifier
kaa.notifier.init('gtk', x11=False)

# kaa.popcorn imports
from kaa.popcorn.utils import Player
from kaa.popcorn.ptypes import *


class GStreamer(Player):
    """
    gstreamer based player
    """
    def __init__(self):
        Player.__init__(self)
        self._gst = None
        self._streaminfo = {}

        # create gst object
        self._gst = gst.element_factory_make("playbin", "player")
        self._gst.get_bus().add_watch(self._gst_message)
        self._timer = kaa.notifier.WeakTimer(self._get_position)


    def set_state(self, state):
        """
        Set state on parent and start/stop position timer.
        """
        self.parent.set_state(state)
        self._timer.stop()
        if state == STATE_PLAYING:
            self._timer.start(0.1)


    def _gst_message(self, bus, msg):
        """
        Message from gstreamer thread.
        """
        # do something clever here
        if msg.type == gst.MESSAGE_STATE_CHANGED:
            old, new, pending = msg.parse_state_changed()
            if new == gst.STATE_PLAYING:
                self.set_state(STATE_PLAYING)
            return True

        if msg.type == gst.MESSAGE_ERROR:
            for e in msg.parse_error():
                if not type(e) == gst.GError:
                    return True
                if e.domain.startswith('gst-stream-error') and \
                       e.code in (gst.STREAM_ERROR_NOT_IMPLEMENTED,
                                  gst.STREAM_ERROR_CODEC_NOT_FOUND,
                                  gst.STREAM_ERROR_TYPE_NOT_FOUND,
                                  gst.STREAM_ERROR_WRONG_TYPE):
                    # unable to play
                    self.set_state(STATE_IDLE)
                    return True
                if e.domain.startswith('gst-resource-error'):
                    self.set_state(STATE_IDLE)
                    return True
                # print e, e.code, e.domain
            return True
        if msg.type == gst.MESSAGE_TAG:
            taglist = msg.parse_tag()
            for key in taglist.keys():
                value = taglist[key]
                if not isinstance(value, (str, unicode, int, long, float)):
                    value = str(value)
                self._streaminfo[key] = value
            self.parent.set_streaminfo(self._streaminfo)
        return True


    def _get_position(self):
        """
        Get stream position and send to parent process.
        """
        usec = self._gst.query_position(gst.FORMAT_TIME)[0]
        pos = float(usec / 1000000) / 1000
        self.parent.set_position(pos)


    #
    # setup from parent
    #

    def configure_video(self, driver, **kwargs):
        """
        Set video driver and parameter.
        """
        if driver == 'xv':
            vo = gst.element_factory_make("xvimagesink", "vo")
            vo.set_xwindow_id(long(kwargs.get('window')))
            vo.set_property('force-aspect-ratio', True)
            goom = gst.element_factory_make("goom", "goom0")
            self._gst.set_property('vis-plugin', goom)
        elif driver == 'none':
            vo = gst.element_factory_make("fakesink", "vo")
        else:
            raise AttributeError('Unsupported video driver %s', driver)
        self._gst.set_property('video-sink', vo)


    def configure_audio(self, driver):
        """
        Set audio driver (oss or alsa).
        """
        ao = gst.element_factory_make("%ssink" % driver, "ao")
        # if alsa: ao.set_property('device', 'hw=0,1')
        self._gst.set_property('audio-sink', ao)



    #
    # commands from parent
    #

    def open(self, uri):
        """
        Open mrl.
        """
        self._gst.set_property('uri', uri)
        self._streaminfo = {}
        self.set_state(STATE_OPEN)


    def play(self):
        """
        Start or resume playback.
        """
        self._gst.set_state(gst.STATE_PLAYING)


    def stop(self):
        """
        Stop playback.
        """
        self._gst.set_state(gst.STATE_NULL)
        self.set_state(STATE_IDLE)


    def pause(self):
        """
        Pause playback.
        """
        self._gst.set_state(gst.STATE_PAUSED)


    def seek(self, value, type):
        """
        SEEK_RELATIVE, SEEK_ABSOLUTE or SEEK_PERCENTAGE.
        """
        pos = 0
        if type == SEEK_RELATIVE:
            current = self._gst.query_position(gst.FORMAT_TIME)[0]
            pos = current + value * 1000000000
        if type == SEEK_ABSOLUTE:
            pos = value * 1000000000
        if type == SEEK_PERCENTAGE and 'duration' in self._streaminfo:
            pos = (self._streaminfo['duration'] / 100) * value
        # seek now
        self._gst.seek(1.0, gst.FORMAT_TIME,
                       gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
                       gst.SEEK_TYPE_SET, pos, gst.SEEK_TYPE_NONE, 0)


    def set_audio_delay(self, delay):
        """
        Sets audio delay.  Positive value defers audio by delay.
        """
        # NYI
        pass
