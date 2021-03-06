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

__all__ = [ 'MediaPlayer', 'runtime_property', 'APPLY_ALWAYS',
            'IGNORE_UNLESS_PLAYING', 'DEFER_UNTIL_PLAYING' ]

# python imports
import sets
import os
import hashlib
import logging

# kaa imports
import kaa
from kaa.utils import property

# kaa.popcorn imports
from kaa.popcorn.ptypes import *
from kaa.popcorn.config import config

# get logging object
log = logging.getLogger('popcorn')

APPLY_ALWAYS          = 'APPLY_ALWAYS'
IGNORE_UNLESS_PLAYING = 'IGNORE_UNLESS_PLAYING'
DEFER_UNTIL_PLAYING   = 'DEFER_UNTIL_PLAYING'

def runtime_policy(type):
    """
    Decorator to mark a property function
    """
    def decorator(func):
        func._runtime_policy = type
        return func
    return decorator


class MediaPlayer(object):
    """
    Base class for players
    """

    _instance_count = 0

    def __init__(self, properties):
        self.signals = {
            "elapsed": kaa.Signal(),
            "stream_changed": kaa.Signal(),
            "frame": kaa.Signal(),
            "osd_configure": kaa.Signal(),
            "state_changed": kaa.Signal(),
        }
        self._state = STATE_IDLE
        self._window = None
        self._position = 0.0
        self._properties = properties
        self._instance_id = "popcorn-%d-%d" % (os.getpid(), self._instance_count)
        MediaPlayer._instance_count += 1

        # some variables for the inherting class the generic player will
        # access at some point.
        self.streaminfo = {}

        # shared memory keys
        key = hashlib.md5(self._instance_id + "osd").hexdigest()[:7]
        self._osd_shmkey = int(key, 16)
        self._osd_shmem = None
        key = hashlib.md5(self._instance_id + "frame").hexdigest()[:7]
        self._frame_shmkey = int(key, 16)
        self._frame_shmem = None

        self._property_callbacks = {}
        self._property_delayed = []
        for name in dir(self):
            func = getattr(self.__class__, name, None)
            if callable(func) and hasattr(func, '_runtime_policy'):
                func = getattr(self, name)
                name = name[10:].replace('_', '-')
                self._property_callbacks[name] = kaa.WeakCallable(func)


    def __repr__(self):
        """
        For debugging only.
        """
        c = str(self.__class__)
        return '<popcorn%s' % c[c.rfind('.'):]


    @property
    def state(self):
        """
        Get current state.
        """
        return self._state


    @state.setter
    def state(self, state):
        """
        Set state and emit 'failed', 'start' or 'end' signal if needed.
        """
        if self._state == state:
            return
        if state == STATE_IDLE and self._state == STATE_SHUTDOWN:
            return
        old_state = self._state
        self._state = state
        if state == STATE_PLAYING and self._property_delayed:
            # now set changed properties
            for key, value in self._property_delayed:
                self.set_property(key, value)
            self._property_delayed = []
        self.signals['state_changed'].emit(old_state, state)


    @property
    def position(self):
        """
        Get current playing position.
        """
        return self._position


    @position.setter
    def position(self, pos):
        """
        Set position and emit 'elapsed' signal.
        """
        if self._position == pos:
            return
        self._position = pos
        self.signals['elapsed'].emit(pos)


    #
    # used only by inheriting player
    #

    @property
    def aspect(self):
        """
        Get aspect ration values. Returns a tuple monitoraspect and a
        tuple with the fullscreen pixel size.
        """
        if not self._window:
            raise AttributeError("No window set")
        if hasattr(self._window, 'get_size'):
            size = self._window.get_size()
        else:
            # kaa.candy widget
            size = self._window.width, self._window.height
        if hasattr(self._window, 'get_display'):
            size = self._window.get_display().get_size()
        aspect = [ int(x) for x in config.video.monitoraspect.split(':') ]
        return aspect, size


    @property
    def pixel_aspect(self):
        """
        Get pixel aspect ratio based on monitoraspect and window size
        """
        a, fs = self.aspect
        return (float(a[0])/a[1]) / (float(fs[0])/fs[1])


    #
    # interface for generic
    #

    def set_window(self, window):
        """
        Set a window for the player.
        """
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


    def get_capabilities(self):
        """
        Return player capabilities.
        """
        return self._player_caps


    def has_capability(self, cap):
        """
        Return if the player has the given capability.
        """
        supported_caps = self.get_capabilities()
        if type(cap) not in (list, tuple):
            return cap in supported_caps
        return sets.Set(cap).issubset(sets.Set(supported_caps))


    #
    # Methods to be implemented by subclasses.
    #

    # Please set self.state when something changes, signals will be send
    # by this base class when you change the state. The following states
    # are valid:
    #
    # STATE_NOT_RUNNING:
    #   the player is not running and has released audio and video
    #   device. It doesn't matter if a child process is still running
    #   or not.
    # STATE_IDLE:
    #   the player is not running but may still have video and audio
    #   devices locked for a next file.
    # STATE_OPENING:
    #   the player is about to open the file and will start playing in
    #   a few seconds. If the player goes from STATE_OPENING to
    #   STATE_IDLE or STATE_NOT_RUNNING again without being in
    #   STATE_PLAYING, the 'failed' signal will be emited.
    # STATE_PLAYING:
    #   player is playing
    # STATE_PAUSED:
    #   player is in playback mode but pausing
    # STATE_SHUTDOWN:
    #   player is going releasing the video and audio devices, next
    #   state has to be STATE_NOT_RUNNING
    #

    def open(self, media):
        """
        Open media (kaa.metadata object).
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


    def set_property(self, prop, value):
        """
        Set a property to a new value.
        """
        if not prop in self._property_callbacks:
            # no special handler, set and return
            self._properties[prop] = value
            return
        func = self._property_callbacks[prop]
        if self.state not in (STATE_PAUSED, STATE_PLAYING):
            # We are not in playback mode.
            if func._runtime_policy == DEFER_UNTIL_PLAYING:
                # delay property call until playing
                self._property_delayed.append((prop, value))
                return
            if func._runtime_policy == IGNORE_UNLESS_PLAYING:
                # just set and return
                self._properties[prop] = value
                return
        # call property function
        if func(value) is not False:
            self._properties[prop] = value


    #
    # For CAP_OSD
    #

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


    #
    # For CAP_CANVAS
    #

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
