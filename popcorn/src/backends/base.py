# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# base.py - Base class (protocol) for backend players
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
import sets

# kaa imports
import kaa.notifier

# kaa.popcorn imports
from kaa.popcorn.ptypes import *
from kaa.popcorn.utils import parse_mrl

class MediaPlayer(object):
    """
    Base class for players
    """

    def __init__(self):
        self.signals = {
            "pause": kaa.notifier.Signal(),
            "play": kaa.notifier.Signal(),
            "pause_toggle": kaa.notifier.Signal(),
            "seek": kaa.notifier.Signal(),
            "start": kaa.notifier.Signal(),
            "failed": kaa.notifier.Signal(),
            # Stream ended (either stopped by user or finished)
            "end": kaa.notifier.Signal(),
            "stream_changed": kaa.notifier.Signal(),
            "frame": kaa.notifier.Signal(), # CAP_CANVAS
            "osd_configure": kaa.notifier.Signal(),  # CAP_OSD

            # Player released video and audio devices
            "release": kaa.notifier.Signal(),

            # Process died (shared memory will go away)
            "shm_quit": kaa.notifier.Signal()
        }

        self._state_object = STATE_IDLE
        self._window = None
        self._size = None
        self._config = None


    def get_capabilities(self):
        """
        Return player capabilities.
        """
        return self._player_caps        # filled by generic


    def get_supported_schemes(self):
        """
        Return supported schemes.
        """
        return self._player_schemes     # filled by generic


    def has_capability(self, cap):
        """
        Return if the player has the given capability.
        """
        supported_caps = self.get_capabilities()
        if type(cap) not in (list, tuple):
            return cap in supported_caps
        return sets.Set(cap).issubset(sets.Set(supported_caps))


    # config setting

    def set_config(self, config):
        """
        Set config object.
        """
        self._config = config


    # state handling

    def get_state(self):
        """
        Get current state.
        """
        return self._state_object


    def _set_state(self, state):
        """
        Set state and emit 'failed', 'start' or 'end' signal if needed.
        """
        if self._state_object == state:
            return

        old_state = self._state_object
        self._state_object = state

        if old_state == STATE_OPENING and state in (STATE_IDLE, STATE_NOT_RUNNING):
            # From STATE_OPENING to not playing. This means something went
            # wrong and the player failed to play.
            self.signals["failed"].emit()

        if old_state == STATE_OPENING and \
               state in (STATE_PLAYING, STATE_PAUSED):
            # From STATE_OPENING to playing. Signal playback start
            self.signals["start"].emit()

        if old_state in (STATE_PLAYING, STATE_PAUSED) and \
               state in (STATE_IDLE, STATE_NOT_RUNNING):
            # From playing to finished. Signal end.
            self.signals["end"].emit()

        if state == STATE_NOT_RUNNING == self._state_object:
            self.signals["release"].emit()
            self.signals["shm_quit"].emit()

    # state property based on get_state and _set_state
    _state = property(get_state, _set_state, None, 'state of the player')


    def set_window(self, window):
        """
        Set a window for the player.
        """
        if not self.has_capability(CAP_VIDEO):
            raise PlayerCapError, "Player doesn't have CAP_VIDEO"
        self._window = window


    def is_paused(self):
        """
        Return if the player is paused.
        """
        return self.state == STATE_PAUSED


    def is_playing(self):
        """
        Return if the player is playing.
        """
        return self.state == STATE_PLAYING


    def set_size(self, size):
        """
        Set a new output size.
        """
        if not self.has_capability(CAP_VIDEO):
            raise PlayerCapError, "Player doesn't have CAP_VIDEO"
        self._size = size


    #
    # Methods to be implemented by subclasses.
    #

    def open(self, mrl):
        """
        Open mrl.
        """
        pass


    def play(self):
        """
        Start playback.
        """
        pass


    def stop(self):
        """
        Stop playback.
        """
        pass


    def pause(self):
        """
        Pause playback.
        """
        pass


    def resume(self):
        """
        Resume playback.
        """
        pass


    def release(self):
        """
        Release audio and video devices.
        """
        self.die()


    def seek_relative(self, offset):
        """
        Seek relative.
        """
        pass


    def seek_absolute(self, position):
        """
        Seek absolute.
        """
        pass


    def seek_percentage(self, percent):
        """
        Seek percentage.
        """
        pass


    def get_position(self):
        """
        Get current playing position.
        """
        pass


    def get_info(self):
        """
        Returns info about the currently playing stream, or the file that
        has just been opened.
        """
        pass


    def nav_command(self, input):
        """
        Issue the navigation command to the player.  'input' is a string
        that contains the command.  See Player class for possible
        values and more documentation.

        Returns True if the nav command is valid for the player, or False
        otherwise.
        """
        return False


    def is_in_menu(self):
        """
        Return True if the player is in a navigation menu.
        """
        return False


    # For CAP_OSD

    def osd_update(self, alpha = None, visible = None, invalid_regions = None):
        """
        Updates the player OSD.  See Player.osd_update() for full doc.
        """
        pass


    def osd_can_update(self):
        """
        Returns True if it's safe to write to the OSD shmem buffer.

        See Player class for full doc.
        """
        pass


    # For CAP_CANVAS

    def set_frame_output_mode(self, vo = None, notify = None, size = None):
        """
        Controls if and how frames are delivered via the 'frame' signal.

        See Player class for full doc.
        """
        pass


    def unlock_frame_buffer(self):
        """
        Unlocks the frame buffer provided by 'frame' signal.

        See Player class for full doc.
        """
        pass
