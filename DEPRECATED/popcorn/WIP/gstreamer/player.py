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
from kaa import WeakCallable

# kaa.popcorn imports
from kaa.popcorn.backends.base import MediaPlayer, runtime_policy, \
     APPLY_ALWAYS, IGNORE_UNLESS_PLAYING, DEFER_UNTIL_PLAYING
from kaa.popcorn.ptypes import *
from kaa.popcorn.config import config
from kaa.popcorn.utils import ChildProcess


class GStreamer(MediaPlayer):

    def __init__(self, properties):
        super(GStreamer, self).__init__(properties)
        self.state = STATE_NOT_RUNNING
        self._gst = None


    def _child_exited(self, exitcode):
        self.state = STATE_NOT_RUNNING
        self._gst = None


    # public API

    def open(self, media):
        """
        Open media.
        """
        self._mrl = media.url
        if not self._gst:
            script = os.path.join(os.path.dirname(__file__), 'main.py')
            self._gst = ChildProcess(self, script)
            self._gst.set_stop_command(WeakCallable(self._gst.die))
            self._gst.start().connect_weak(self._child_exited)
        self.position = 0.0
        self.state = STATE_OPENING
        self._gst.open(self._mrl)
        if self._window:
            aspect, size = self.aspect
            self._gst.configure_video('xv', window=self._window.get_id(),
                                      aspect=aspect, size=size)
        else:
            self._gst.configure_video('none')
        self._gst.configure_audio(config.audio.driver)


    def play(self):
        """
        Start playback.
        """
        self._gst.play()


    def stop(self):
        """
        Stop playback.
        """
        self.state = STATE_STOPPING
        self._gst.stop()


    def pause(self):
        """
        Pause playback.
        """
        self._gst.pause()
        self.state = STATE_PAUSED


    def resume(self):
        """
        Resume playback.
        """
        self._gst.play()
        self.state = STATE_PLAYING


    def release(self):
        """
        Release audio and video devices.
        """
        if self._gst:
            self.state = STATE_SHUTDOWN
            self._gst.die()


    def seek(self, value, type):
        """
        SEEK_RELATIVE, SEEK_ABSOLUTE or SEEK_PERCENTAGE.
        """
        self._gst.seek(value, type)


    @runtime_policy(DEFER_UNTIL_PLAYING)
    def _set_prop_audio_delay(self, delay):
        """
        Sets audio delay. Positive value defers audio by delay.
        """
        self._gst.set_audio_delay(delay)
