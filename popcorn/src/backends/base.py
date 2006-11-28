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
import os
import md5
import logging

# kaa imports
import kaa.notifier

# kaa.popcorn imports
from kaa.popcorn.ptypes import *
from kaa.popcorn.utils import parse_mrl

# get logging object
log = logging.getLogger('popcorn')


class MediaPlayer(object):
    """
    Base class for players
    """

    _instance_count = 0

    def __init__(self):
        self.signals = {
            "elapsed": kaa.notifier.Signal(),
            "stream_changed": kaa.notifier.Signal(),
            "frame": kaa.notifier.Signal(),
            "osd_configure": kaa.notifier.Signal(),
        }
        self._state_changed = kaa.notifier.Signal()
        self._state_object = STATE_IDLE
        self._window = None
        self._size = None
        self._aspect = None
        self._config = None
        self._instance_id = "popcorn-%d-%d" % (os.getpid(), self._instance_count)
        MediaPlayer._instance_count += 1

        # some variables for the inherting class
        self._position_value = 0.0
        self._streaminfo = {}
        
        # shared memory keys
        key = md5.md5(self._instance_id + "osd").hexdigest()[:7]
        self._osd_shmkey = int(key, 16)
        self._osd_shmem = None
        key = md5.md5(self._instance_id + "frame").hexdigest()[:7]
        self._frame_shmkey = int(key, 16)
        self._frame_shmem = None
        

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

        self._state_changed.emit(old_state, state)

    # state property based on get_state and _set_state
    _state = property(get_state, _set_state, None, 'state of the player')


    # position handling

    def get_position(self):
        """
        Get current playing position.
        """
        return self._position_value


    def _set_position(self, pos):
        """
        Set position and emit 'elapsed' signal.
        """
        if self._position_value == pos:
            return
        self._position_value = pos
        self.signals['elapsed'].emit(pos)

    # position property based on get_state and _set_state
    _position = property(get_position, _set_position, None, 'player position')

 
    def get_audio_delay(self):
        """
        Returns the audio delay set by set_audio_delay()
        """
        return self._audio_delay


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


    def set_size(self, size, aspect=None):
        """
        Set a new output size.
        """
        if not self.has_capability(CAP_VIDEO):
            raise PlayerCapError, "Player doesn't have CAP_VIDEO"
        self._size = size
        self._aspect = aspect
        if not aspect and size and size[0] and size[1]:
            self._aspect = float(size[0]) / size[1]


    def get_size(self):
        """
        Get output size.
        """
        if not self.has_capability(CAP_VIDEO):
            raise PlayerCapError, "Player doesn't have CAP_VIDEO"
        return self._size


    def set_aspect(self, aspect=None):
        """
        Set special output aspect ratio.
        """
        if not self.has_capability(CAP_VIDEO):
            raise PlayerCapError, "Player doesn't have CAP_VIDEO"
        self._aspect = aspect


    def get_aspect(self):
        """
        Get output aspect ratio.
        """
        if not self.has_capability(CAP_VIDEO):
            raise PlayerCapError, "Player doesn't have CAP_VIDEO"
        return self._aspect


    #
    # Methods to be implemented by subclasses.
    #

    # Please set self._state when something changes, signals will be send
    # by this base class when you change the state. The following states
    # are valid:

    # STATE_NOT_RUNNING: the player is not running and has released audio
    #     and video device. It doesn't matter if a child process is still
    #     running or not.
    # STATE_IDLE: the player is not running but may still have video and
    #     audio devices locked for a next file.
    # STATE_OPENING: the player is about to open the file and will start
    #     playing in a few seconds. If the player goes from STATE_OPENING
    #     to STATE_IDLE or STATE_NOT_RUNNING again without being in
    #     STATE_PLAYING, the 'failed' signal will be emited.
    # STATE_PLAYING: player is playing
    # STATE_PAUSED: player is in playback mode but pausing
    # STATE_SHUTDOWN: player is going releasing the video and audio devices,
    #     next state has to be STATE_NOT_RUNNING

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
        pass


    def seek(self, value, type):
        """
        Seek. Possible types are SEEK_RELATIVE, SEEK_ABSOLUTE and SEEK_PERCENTAGE.
        """
        pass


    def get_info(self):
        """
        Returns info about the currently playing stream, or the file that
        has just been opened.
        """
        return self._streaminfo


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
