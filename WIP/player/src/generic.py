# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# generic.py - Generic Player Interface
# -----------------------------------------------------------------------------
# $Id$
#
# This module defines a generic player class used by the application. It will
# use a player from backends for the real playback.
#
# -----------------------------------------------------------------------------
# kaa-player - Generic Player API
# Copyright (C) 2006 Jason Tackaberry, Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
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

all = [ 'Player' ]

# python imports
import logging

# kaa imports
import kaa.notifier

# kaa.player imports
from ptypes import *
from skeleton import MediaPlayer
from backends.manager import get_player_class, get_all_players

# get logging object
log = logging.getLogger('player')

class Player(object):
    """
    Generic player. On object of this class will use the players from the
    backend subdirectory for playback.
    """
    def __init__(self, window):

        self._player = None
        self._size = window.get_size()
        self._window = window

        self.signals = {
            "pause": kaa.notifier.Signal(),
            "play": kaa.notifier.Signal(),
            "pause_toggle": kaa.notifier.Signal(),
            "seek": kaa.notifier.Signal(),
            "open": kaa.notifier.Signal(),
            "start": kaa.notifier.Signal(),
            "failed": kaa.notifier.Signal(),
            # Stream ended (either stopped by user or finished)
            "end": kaa.notifier.Signal(),
            "stream_changed": kaa.notifier.Signal(),
            "frame": kaa.notifier.Signal(), # CAP_CANVAS
            "osd_configure": kaa.notifier.Signal(),  # CAP_OSD
            # Process is about to die (shared memory will go away)
            "quit": kaa.notifier.Signal()
        }


    def open(self, mrl, caps = None, player = None):
        """
        Open mrl. The parameter 'caps' defines the needed capabilities the
        player must have. If 'player' is given, force playback with the
        given player.
        """
        cls = get_player_class(mrl = mrl, player = player, caps = caps)
        self._open_mrl = mrl
        self._open_caps = caps

        if not cls:
            raise PlayerError("No supported player found to play %s", mrl)

        if self._player != None:
            running = self.get_state() != STATE_IDLE
            self._player.stop()
            if isinstance(self._player, cls):
                return self._player.open(mrl)

            # Continue open once our current player is dead.  We want to wait
            # before spawning the new one so that it releases the audio
            # device.
            if running:
                self._player.signals["quit"].connect_once(self._open, mrl, cls)
                self._player.die()
                return

        return self._open(mrl, cls)


    def _open(self, mrl, cls):
        """
        The real open function called from 'open'.
        """
        self._player = cls()

        for sig in self.signals:
            if sig in self._player.signals and \
                   not sig in ('start', 'failed', 'open'):
                self._player.signals[sig].connect_weak(self.signals[sig].emit)

        self._player.open(mrl)
        self._player.set_window(self._window)
        self._player.set_size(self._size)
        self.signals['open'].emit()


    @kaa.notifier.yield_execution()
    def play(self, __player_list=None, **kwargs):
        """
        Play the opened mrl with **kwargs. This function may return an
        InProgress object which will be finished once the playing is
        started or failed to start.
        """
        if self.get_state() in (STATE_PLAYING, STATE_PAUSED):
            self._player.play(**kwargs)

        if not self._player:
            raise PlayerError, "play called before open"
            yield False

        if self._open in self._player.signals["quit"]:
            # wait for old player to die
            block = kaa.notifier.InProgress()
            self.signals['open'].connect_once(block.finished, True)
            yield block

        state = self._player.get_state()
        self._player.play(**kwargs)
        if state == self._player.get_state() or \
               self._player.get_state() != STATE_OPENING:
            yield True

        # wait for 'start' or 'failed'
        block = kaa.notifier.InProgress()
        self._player.signals['failed'].connect_once(block.finished, False)
        self._player.signals['start'].connect_once(block.finished, True)
        yield block
        self._player.signals['failed'].disconnect(block.finished)
        self._player.signals['start'].disconnect(block.finished)

        if not block():
            # failed, try more player
            if __player_list is None:
                # FIXME: only try player with needed caps
                __player_list = get_all_players()
            if self._player._player_id in __player_list:
                __player_list.remove(self._player._player_id)
            if not __player_list:
                # no more player to try
                self.signals['failed'].emit()
                yield False
            # try next
            log.warning('unable to play with %s, try %s',
                        self._player._player_id, __player_list[0])
            self.open(self._open_mrl, self._open_caps, player=__player_list[0])
            sync = self.play(__player_list, **kwargs)
            # wait for the recursive call to return and return the
            # given value (True or False)
            yield sync
            yield sync()
        # playing
        self.signals['start'].emit()
        yield True


    # Player API

    def stop(self):
        """
        Stop playback.
        """
        if self._player:
            self._player.stop()


    def pause(self):
        """
        Pause playback.
        """
        if self._player:
            self._player.pause()


    def pause_toggle(self):
        """
        Toggle play / pause.
        """
        state = self.get_state()
        if state == STATE_PLAYING:
            self._player.pause()
        if state == STATE_PAUSED:
            self._player.play()


    def seek_relative(self, offset):
        """
        Seek relative.
        """
        if self._player:
            self._player.seek_relative(offset)


    def seek_absolute(self, position):
        """
        Seek absolute.
        """
        if self._player:
            self._player.seek_absolute(position)


    def seek_percentage(self, percent):
        """
        Seek percentage.
        """
        if self._player:
            self._player.seek_percent(position)


    def get_position(self):
        """
        Get current playing position.
        """
        if self._player:
            return self._player.get_position()
        return 0.0


    def get_info(self):
        """
        Get information about the stream.
        """
        if self._player:
            return self._player.get_info()
        return {}


    def nav_command(self, input):
        """
        Get navigation command.
        """
        if self._player:
            self._player.nav_command(input)
        return False


    def is_in_menu(self):
        """
        Return True if the player is in a navigation menu.
        """
        if self._player:
            return self._player.is_in_menu()
        return False


    def get_player_id(self):
        """
        Get id of current player.
        """
        if self._player:
            return self._player._player_id
        return ''


    def get_window(self):
        """
        Get window used by the player.
        """
        return self._window


    def get_state(self):
        """
        Get state of the player. Note: STATE_NOT_RUNNING is for internal use.
        This function will return STATE_IDLE if the player is not running.
        """
        if self._player and self._player.get_state() != STATE_NOT_RUNNING:
            return self._player.get_state()
        return STATE_IDLE


    def get_size(self):
        """
        Get output size.
        """
        return self._size


    def set_size(self, size):
        """
        Set output size.
        """
        self._size = size
        if self._player:
            return self._player.set_size(size)


    def has_capability(self, cap):
        """
        Return if the player has the given capability.
        """
        if self._player:
            return self._player.has_capability(cap)
        return False


    # For CAP_OSD

    def osd_can_update(self):
        """
        Return True if the player has an ODS to update.
        """
        if self._player:
            return self._player.osd_can_update()
        return False


    def osd_update(self, *args, **kwargs):
        """
        Update player OSD.
        """
        if self._player:
            return self._player.osd_update(*args, **kwargs)


    # For CAP_CANVAS

    def set_frame_output_mode(self, vo = None, notify = None, size = None):
        """
        If vo is True, render video to the vo driver's video window.  If
        False, suppress.  If notify is True, emit 'frame' signal when new
        frame available.  size is a 2-tuple containing the target size of the
        frame as given to the 'frame' signal callback.  If any are None, do
        not alter the status since last call.
        """
        if self._player:
            return self._player.set_frame_output_mode()


    def unlock_frame_buffer(self):
        """
        Unlocks the frame buffer provided by 'frame' signal.
        """
        if self._player:
            return self._player.unlock_frame_buffer()
