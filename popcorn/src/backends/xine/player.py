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
import kaa.shm
import kaa.xine as xine

# kaa.popcorn imports
from kaa.popcorn.backends.base import MediaPlayer, runtime_policy, \
     APPLY_ALWAYS, IGNORE_UNLESS_PLAYING, DEFER_UNTIL_PLAYING
from kaa.popcorn.ptypes import *
from kaa.popcorn.config import config
from kaa.popcorn.utils import ChildProcess

# get logging object
log = logging.getLogger('popcorn.xine')

BUFFER_UNLOCKED = 0x10
BUFFER_LOCKED = 0x20

class Xine(MediaPlayer):

    def __init__(self, properties):
        super(Xine, self).__init__(properties)
        self._is_in_menu = False
        self._cur_frame_output_mode = [True, False, None] # vo, shmem, size
        self._locked_buffer_offsets = []
        self._child_spawn()


    #
    # child handling
    #

    def _child_spawn(self):
        # Launch self (-u is unbuffered stdout)
        script = os.path.join(os.path.dirname(__file__), 'main.py')
        # Put this into ChildProcess to enable gdb traces. It is deactivated
        # as default because it messes up kaa shutdown handling.
        # gdb = log.getEffectiveLevel() == logging.DEBUG
        self._xine = ChildProcess(self, script, gdb=False)
        self._xine.stop_command = kaa.WeakCallable(self._xine.die)
        signal = self._xine.start(str(self._osd_shmkey))
        signal.connect_weak(self._child_exited)
        self._xine_configured = False


    def _child_exited(self, exitcode):
        log.debug('xine child dead')
        self._xine = None
        if self._window:
            # Disconnect signals from existing window.
            disconnect = self._window.signals.disconnect
            disconnect('configure_event', self._window_configure_event)
            disconnect('map_event', self._window_visibility_event)
            disconnect('unmap_event', self._window_visibility_event)
            disconnect('expose_event', self._window_expose_event)

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
            except kaa.shm.error:
                pass
            self._frame_shmem = None
        self.state = STATE_NOT_RUNNING


    #
    # Commands from child
    #

    def _child_set_status(self, pos, time, length, status, speed):
        old_pos = self.position
        if self.state in (STATE_PAUSED, STATE_PLAYING, STATE_OPEN) and time is not None:
            self.position = float(time)
        if length is not None:
            self.streaminfo["length"] = length

        if status == 2:
            if self.state in (STATE_STOPPING, STATE_SHUTDOWN):
                # ignore the status update, we are stopping the player
                return
            if self.state not in (STATE_PAUSED, STATE_PLAYING):
                self.state = STATE_PLAYING
            if speed == xine.SPEED_PAUSE and self.state != STATE_PAUSED:
                self.state = STATE_PAUSED
            elif speed > xine.SPEED_PAUSE and self.state != STATE_PLAYING:
                prev_state = self.state
                self.state = STATE_PLAYING
            # TODO:
            # if self.position - old_pos < 0 or self.position - old_pos > 1:
            # self.signals["seek"].emit(self.position)
        elif status in (0, 1):
            if self.state in (STATE_PAUSED, STATE_PLAYING):
                # Stream ended.
                log.debug('xine stream ended')
                self.state = STATE_IDLE


    def _child_osd_configure(self, width, height, aspect):
        if not self._osd_shmem:
            shmid = kaa.shm.getshmid(self._osd_shmkey)
            if shmid:
                self._osd_shmem = kaa.shm.memory(shmid)
                self._osd_shmem.attach()

        # TODO: remember these values and emit them to new connections to
        # this signal after this point.
        self.signals["osd_configure"].emit(width, height, self._osd_shmem.addr + 16, width, height)


    def _child_resize(self, size):
        pass
        #self._window.resize(size)


    def _child_set_streaminfo(self, status, info):
        if not status:
            # failed playback
            self.state = STATE_IDLE
            return

        changed = info != self.streaminfo
        self.streaminfo = info

        if self.state == STATE_OPENING:
            self.state = STATE_OPEN

        if changed:
            self.signals["stream_changed"].emit()

    def _child_frame_reconfigure(self, width, height, aspect):
        si = self.streaminfo.copy()
        si.update({
            'width': width,
            'height': height,
            'aspect': aspect
        })
        self._child_set_streaminfo(True, si)

    def _child_xine_event(self, event, data):
        if event == xine.EVENT_UI_NUM_BUTTONS:
            self._is_in_menu = data["num_buttons"] > 0


    def _child_play_stopped(self):
        log.debug('xine stopped')
        if not self.state in (STATE_NOT_RUNNING, STATE_SHUTDOWN):
            self.state = STATE_IDLE


    def _child_frame_notify(self, shmid, offset):
        if not self._frame_shmem or shmid != self._frame_shmem.shmid:
            if self._frame_shmem:
                self._frame_shmem.detach()
            self._frame_shmem = kaa.shm.memory(shmid)
            self._frame_shmem.attach()

        try:
            lock, width, height, aspect = struct.unpack("bhhd", self._frame_shmem.read(16, offset))
        except kaa.shm.error:
            self._frame_shmem.detach()
            self._frame_shmem = None
            return

        if width > 0 and height > 0 and aspect > 0:
            self._locked_buffer_offsets.append(offset)
            a = self._frame_shmem.addr + 32 + offset
            self.signals["frame"].emit(width, height, aspect, a, "yv12")

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
            if self._xine:
                if old_window and window.get_display() == old_window.get_display():
                    # New window on same display, no need to reconfigure the vo,
                    # we can just point at the new window.
                    self._xine.window_changed(window.get_id(), window.get_size(),
                                              self._window.get_visible(), [])
                elif self._xine_configured:
                    # No previous window, must reconfigure vo.
                    self._xine.configure_video(window.get_id(), window.get_size(),
                                               self.pixel_aspect, config.video.colorkey)

        # Sends a window_changed command to slave.
        if window and self._xine:
            self._window_visibility_event()


    def configure(self):
        if self._xine_configured:
            return

        self._xine_configured = True
        self._xine.set_config(config)
        if self._window:
            self._xine.configure_video(self._window.get_id(), self._window.get_size(),
                                       self.pixel_aspect, config.video.colorkey)
        else:
            self._xine.configure_video(None, None, None, None)
        self._xine.configure_audio(config.audio.driver)
        self._xine.configure_stream(self._properties)


    #
    # Methods for MediaPlayer subclasses
    #

    def open(self, media):
        """
        Open media.
        """
        self._is_in_menu = False
        self._mrl = media.url
        if not self._xine:
            self._child_spawn()

        self.configure()
        self.position = 0.0
        log.debug('xine open %s' % self._mrl)
        self._xine.open(self._mrl)
        self.state = STATE_OPENING


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
        self.state = STATE_STOPPING
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
            self.state = STATE_SHUTDOWN
            self._xine.die()


    def seek(self, value, type):
        """
        Seek. Possible types are SEEK_RELATIVE, SEEK_ABSOLUTE and SEEK_PERCENTAGE.
        """
        self._xine.seek(value, type)


    @runtime_policy(DEFER_UNTIL_PLAYING)
    def _set_prop_audio_delay(self, delay):
        """
        Sets audio delay. Positive value defers audio by delay.
        """
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


    def set_property(self, prop, value):
        """
        Set a property to a new value.
        """
        super(Xine, self).set_property(prop, value)
        if self._xine:
            self._xine.set_property(prop, value)

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

        if self.state == STATE_OPENING:
            return

        vo, notify, size = self._cur_frame_output_mode
        log.debug('Setting frame output: vo=%s notify=%s size=%s' % (vo, notify, size))
        self._xine.set_frame_output_mode(vo, notify, size)


    def unlock_frame_buffer(self):
        """
        Unlocks the frame buffer provided by the last 'frame' signal
        See generic.unlock_frame_buffer for details.
        """
        offset = self._locked_buffer_offsets.pop(0)
        try:
            self._frame_shmem.write(chr(BUFFER_UNLOCKED), offset)
        except kaa.shm.error:
            self._frame_shmem.detach()
            self._frame_shmem = None
