# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# xine/player.py - xine backend
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
import md5
import struct
import logging

# kaa imports
import kaa
import kaa.notifier
import kaa.shm
import kaa.xine as xine

# kaa.popcorn imports
from kaa.popcorn.backends.base import MediaPlayer
from kaa.popcorn.utils import ChildProcess, parse_mrl
from kaa.popcorn.ptypes import *

# get logging object
log = logging.getLogger('popcorn.xine')

BUFFER_UNLOCKED = 0x10
BUFFER_LOCKED = 0x20

class Xine(MediaPlayer):

    def __init__(self):
        super(Xine, self).__init__()
        self._check_new_frame_timer = kaa.notifier.WeakTimer(self._check_new_frame)
        self._is_in_menu = False
        self._cur_frame_output_mode = [True, False, None] # vo, shmem, size
        self._child_spawn()


    #
    # child handling
    #

    def _child_spawn(self):
        # Launch self (-u is unbuffered stdout)
        script = os.path.join(os.path.dirname(__file__), 'main.py')
        self._xine = ChildProcess(self, script)
        self._xine.signals["completed"].connect_weak(self._child_exited)
        self._xine.set_stop_command(kaa.notifier.WeakCallback(self._xine.die))
        self._xine.start(str(self._osd_shmkey), str(self._frame_shmkey))
        self._xine_configured = False


    def _child_exited(self, exitcode):
        log.debug('xine child dead')
        self._xine = None

        # remove shared memory
        if self._osd_shmem:
            try:
                self._osd_shmem.detach()
                kaa.shm.remove_memory(self._osd_shmem.shmid)
            except kaa.shm.error:
                # Probably already deleted by child
                pass
            self._osd_shmem = None

        if self._frame_shmem:
            try:
                self._frame_shmem.detach()
                kaa.shm.remove_memory(self._frame_shmem.shmid)
            except kaa.shm.error:
                pass
            self._frame_shmem = None
        self._state = STATE_NOT_RUNNING


    #
    # Commands from child
    #

    def _child_set_status(self, pos, time, length, status, speed):
        old_pos = self._position
        if self.get_state() in (STATE_PAUSED, STATE_PLAYING, STATE_OPEN):
            self._position = float(time)
        self._streaminfo["length"] = length

        if status == 2:
            if self.get_state() not in (STATE_PAUSED, STATE_PLAYING):
                self._state = STATE_PLAYING
            if speed == xine.SPEED_PAUSE and self.get_state() != STATE_PAUSED:
                self._state = STATE_PAUSED
            elif speed > xine.SPEED_PAUSE and self.get_state() != STATE_PLAYING:
                prev_state = self.get_state()
                self._state = STATE_PLAYING
            # TODO:
            # if self._position - old_pos < 0 or self._position - old_pos > 1:
            # self.signals["seek"].emit(self._position)
        elif status in (0, 1):
            if self.get_state() in (STATE_PAUSED, STATE_PLAYING):
                # Stream ended.
                log.debug('xine stream ended')
                self._state = STATE_IDLE


    def _child_osd_configure(self, width, height, aspect):
        if not self._osd_shmem:
            shmid = kaa.shm.getshmid(self._osd_shmkey)
            if shmid:
                self._osd_shmem = kaa.shm.memory(shmid)
                self._osd_shmem.attach()
        if not self._frame_shmem:
            shmid = kaa.shm.getshmid(self._frame_shmkey)
            if shmid:
                self._frame_shmem = kaa.shm.memory(shmid)
                self._frame_shmem.attach()

        # TODO: remember these values and emit them to new connections to
        # this signal after this point.
        self.signals["osd_configure"].emit(\
            width, height, self._osd_shmem.addr + 16, width, height)


    def _child_resize(self, size):
        pass
        #self._window.resize(size)


    def _child_set_streaminfo(self, status, info):
        if not status:
            # failed playback
            self._state = STATE_IDLE
            return

        changed = info != self._streaminfo
        self._streaminfo = info

        if self._state == STATE_OPENING:
            self._state = STATE_OPEN

        if changed:
            self.signals["stream_changed"].emit()


    def _child_xine_event(self, event, data):
        if event == xine.EVENT_UI_NUM_BUTTONS:
            self._is_in_menu = data["num_buttons"] > 0


    def _child_play_stopped(self):
        log.debug('xine stopped')
        if not self._state in (STATE_NOT_RUNNING, STATE_SHUTDOWN):
            self._state = STATE_IDLE


    #
    # Window handling
    #

    def _window_visibility_event(self):
        self._xine.window_changed(self._window.get_id(), self._window.get_size(),
                                   self._window.get_visible(), [])

    def _window_expose_event(self, regions):
        self._xine.window_changed(self._window.get_id(), self._window.get_size(),
                                   self._window.get_visible(), regions)

    def _window_configure_event(self, pos, size):
        self._xine.window_changed(self._window.get_id(), size,
                                   self._window.get_visible(), [])

    def set_window(self, window):
        """
        Set a window for the player (override from MediaPlayer)
        """
        old_window = self._window
        super(Xine, self).set_window(window)

        if old_window and old_window != self._window:
            # Disconnect signals from existing window.
            old_window.signals["configure_event"].disconnect(self._window_configure_event)
            old_window.signals["map_event"].disconnect(self._window_visibility_event)
            old_window.signals["unmap_event"].disconnect(self._window_visibility_event)
            old_window.signals["expose_event"].disconnect(self._window_expose_event)

        if window and window.signals and old_window != self._window:
            window.signals["configure_event"].connect_weak(self._window_configure_event)
            window.signals["map_event"].connect_weak(self._window_visibility_event)
            window.signals["unmap_event"].connect_weak(self._window_visibility_event)
            window.signals["expose_event"].connect_weak(self._window_expose_event)

        # Sends a window_changed command to slave.
        if window:
            self._window_visibility_event()


    #
    # Methods for MediaPlayer subclasses
    #

    def open(self, mrl):
        """
        Open mrl.
        """
        scheme, path = parse_mrl(mrl)
        if scheme not in self.get_supported_schemes():
            raise ValueError, "Unsupported mrl scheme '%s'" % scheme
        self._mrl = "%s:%s" % (scheme, path)
        if not self._xine:
            self._child_spawn()

        if not self._xine_configured:
            self._xine_configured = True
            self._xine.set_config(self._config)
            if self._window:
                self._xine.configure_video(self._window.get_id(), self.get_aspect())
            else:
                self._xine.configure_video(None, None)
            self._xine.configure_audio(self._config.audio.driver)
            self._xine.configure_stream()
        self._position = 0.0
        self._audio_delay = 0.0
        log.debug('xine open')
        self._xine.open(self._mrl)
        self._state = STATE_OPENING


    def play(self):
        """
        Start playback.
        """
        log.debug('play')
        self._xine.play()
        self.set_frame_output_mode()


    def stop(self):
        """
        Stop playback.
        """
        log.debug('xine stop')
        self._xine.stop()


    def pause(self):
        """
        Pause playback.
        """
        self._xine.pause()


    def resume(self):
        """
        Resume playback.
        """
        self._xine.resume()


    def release(self):
        """
        Release audio and video devices.
        """
        if self._xine:
            self._state = STATE_SHUTDOWN
            self._xine.die()


    def seek(self, value, type):
        """
        Seek. Possible types are SEEK_RELATIVE, SEEK_ABSOLUTE and SEEK_PERCENTAGE.
        """
        self._xine.seek(value, type)


    def set_audio_delay(self, delay):
        """
        Sets audio delay.  Positive value defers audio by delay.
        """
        self._audio_delay = delay
        self._xine.set_audio_delay(delay)


    def nav_command(self, input):
        """
        Issue the navigation command to the player.
        """
        map = {
            "up": xine.EVENT_INPUT_UP,
            "down": xine.EVENT_INPUT_DOWN,
            "left": xine.EVENT_INPUT_LEFT,
            "right": xine.EVENT_INPUT_RIGHT,
            "select": xine.EVENT_INPUT_SELECT,
            "prev": xine.EVENT_INPUT_PREVIOUS,
            "next": xine.EVENT_INPUT_NEXT,
            "angle_prev": xine.EVENT_INPUT_ANGLE_PREVIOUS,
            "angle_next": xine.EVENT_INPUT_ANGLE_NEXT,
            "menu1": xine.EVENT_INPUT_MENU1,
            "menu2": xine.EVENT_INPUT_MENU2,
            "menu3": xine.EVENT_INPUT_MENU3,
            "menu4": xine.EVENT_INPUT_MENU4,
            "0": xine.EVENT_INPUT_NUMBER_0,
            "1": xine.EVENT_INPUT_NUMBER_1,
            "2": xine.EVENT_INPUT_NUMBER_2,
            "3": xine.EVENT_INPUT_NUMBER_3,
            "4": xine.EVENT_INPUT_NUMBER_4,
            "5": xine.EVENT_INPUT_NUMBER_5,
            "6": xine.EVENT_INPUT_NUMBER_6,
            "7": xine.EVENT_INPUT_NUMBER_7,
            "8": xine.EVENT_INPUT_NUMBER_8,
            "9": xine.EVENT_INPUT_NUMBER_9
        }
        if input in map:
            self._xine.input(map[input])
            return True
        return False


    def is_in_menu(self):
        """
        Return True if the player is in a navigation menu.
        """
        return self._is_in_menu


    #
    # Methods and helper for MediaPlayer subclasses for CAP_OSD
    #

    def osd_can_update(self):
        """
        Returns True if it is safe to write to the player's shared memory
        buffer used for OSD, and False otherwise.  If this buffer is written
        to even though this function returns False, the OSD may exhibit
        corrupt output or tearing during animations.
        See generic.osd_can_update for details.
        """
        if not self._osd_shmem:
            return False

        try:
            if ord(self._osd_shmem.read(1)) == BUFFER_UNLOCKED:
                return True
        except kaa.shm.error:
            self._osd_shmem.detach()
            self._osd_shmem = None

        return False


    def osd_update(self, alpha = None, visible = None, invalid_regions = None):
        """
        Updates the OSD of the player based on the given argments.
        See generic.osd_update for details.
        """
        self._xine.osd_update(alpha, visible, invalid_regions)



    #
    # Methods and helper for MediaPlayer subclasses for CAP_CANVAS
    #

    def set_frame_output_mode(self, vo = None, notify = None, size = None):
        """
        Controls if and how frames are delivered via the 'frame' signal, and
        whether or not frames are drawn to the vo driver's video window.
        See generic.set_frame_output_mode for details.
        """
        if vo != None:
            self._cur_frame_output_mode[0] = vo
        if notify != None:
            self._cur_frame_output_mode[1] = notify
        if size != None:
            self._cur_frame_output_mode[2] = size

        if self.get_state() == STATE_OPENING:
            return

        vo, notify, size = self._cur_frame_output_mode

        if notify:
            self._check_new_frame_timer.start(0.01)
        else:
            self._check_new_frame_timer.stop()

        self._xine.set_frame_output_mode(vo, notify, size)


    def unlock_frame_buffer(self):
        """
        Unlocks the frame buffer provided by the last 'frame' signal
        See generic.unlock_frame_buffer for details.
        """
        try:
            self._frame_shmem.write(chr(BUFFER_UNLOCKED))
        except kaa.shm.error:
            self._frame_shmem.detach()
            self._frame_shmem = None


    def _check_new_frame(self):
        if not self._frame_shmem:
            return

        try:
            lock, width, height, aspect = struct.unpack(\
                "hhhd", self._frame_shmem.read(16))
        except kaa.shm.error:
            self._frame_shmem.detach()
            self._frame_shmem = None
            return

        if lock & BUFFER_UNLOCKED:
            return

        if width > 0 and height > 0 and aspect > 0:
            a = self._frame_shmem.addr + 16
            self.signals["frame"].emit(width, height, aspect, a, "bgr32")
