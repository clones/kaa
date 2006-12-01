# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# gstreamer/player.py - gstreamer backend
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
import sys
import os

# kaa imports
from kaa.notifier import WeakCallback

# kaa.popcorn imports
from kaa.popcorn.backends.base import MediaPlayer
from kaa.popcorn.ptypes import *
from kaa.popcorn.utils import ChildProcess


class GStreamer(MediaPlayer):

    def __init__(self, config):
        super(GStreamer, self).__init__(config)
        self._state = STATE_NOT_RUNNING
        self._gst = None


    def _child_exited(self, exitcode):
        self._state = STATE_NOT_RUNNING
        self._gst = None


    # public API

    def open(self, mrl):
        """
        Open mrl.
        """
        if mrl.find('://') == -1:
            mrl = 'file://' + mrl
        self._mrl = mrl
        if not self._gst:
            script = os.path.join(os.path.dirname(__file__), 'main.py')
            self._gst = ChildProcess(self, script)
            self._gst.signals["completed"].connect_weak(self._child_exited)
            self._gst.set_stop_command(WeakCallback(self._gst.die))
            self._gst.start()
        self._position = 0.0
        self._state = STATE_OPENING
        self._gst.open(self._mrl)
        if self._window:
            self._gst.configure_video('xv', window=self._window.get_id())
        else:
            self._gst.configure_video('none')
        self._gst.configure_audio(self._config.audio.driver)


    def play(self):
        """
        Start playback.
        """
        self._gst.play()


    def stop(self):
        """
        Stop playback.
        """
        self._state = STATE_STOPPING
        self._gst.stop()


    def pause(self):
        """
        Pause playback.
        """
        self._gst.pause()
        self._state = STATE_PAUSED


    def resume(self):
        """
        Resume playback.
        """
        self._gst.play()
        self._state = STATE_PLAYING


    def release(self):
        """
        Release audio and video devices.
        """
        if self._gst:
            self._state = STATE_SHUTDOWN
            self._gst.die()


    def seek(self, value, type):
        """
        SEEK_RELATIVE, SEEK_ABSOLUTE or SEEK_PERCENTAGE.
        """
        self._gst.seek(value, type)


    def set_audio_delay(self, delay):
        """
        Sets audio delay.  Positive value defers audio by delay.
        """
        self._audio_delay = delay
        self._gst.set_audio_delay(delay)
