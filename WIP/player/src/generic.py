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
            # Emitted when a new frame is availabnle.  See 
            # set_frame_output_mode() doc for more info.
            "frame": kaa.notifier.Signal(), # CAP_CANVAS
            # Emitted when OSD buffer has changed.  See osd_update() doc
            # for more info.
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
            # wait for the recursive call to return
            yield sync
            # now the recursive call is finished. We return the result to signal
            # if playing is started (True) or failed (False).
            status = sync()
            yield status
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
        Issue the navigation command to the player.  'input' is a string
        that contains the command.  Valid commands are: up, down, left, right,
        select, prev, next, angle_prev, angle_next, menu1, menu2, menu3, menu4,
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9.

        Returns True if the nav command is valid for the player, or False
        otherwise.
        """
        if self._player:
            return self._player.nav_command(input)
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
        Returns True if it is safe to write to the player's shared memory
        buffer used for OSD, and False otherwise.  If this buffer is written
        to even though this function returns False, the OSD may exhibit 
        corrupt output or tearing during animations.

        The shared memory buffer is provided when the player starts via the
        'osd_configure' signal.  See osd_update() for more details.
        """
        if self._player:
            return self._player.osd_can_update()
        return False


    def osd_update(self, alpha = None, visible = None, invalid_regions = None):
        """
        Updates the OSD of the player based on the given argments:
            alpha:  
                the global alpha level of the OSD, 0 <= x <= 256.  255 means
                fully opaque, but per-pixel alpha is still considered.  If
                alpha is 256, the alpha channel of the OSD buffer is ignored
                and the OSD will fully obstruct the video.  0 is equivalent
                to setting visible=False.

            visible: 
                True if the OSD should be visible, False otherwise.  The
                default state is False.

            invalid_regions: 
                A list of 4-tuples (left, top, width, height) that indicate
                regions of the OSD shmem buffer that have been written to and
                require synchronization with the actual OSD of the player.
                
        It is guaranteed that all OSD changes contained in single osd_update()
        call will be reflected between frames.  Multiple, sequential calls to
        osd_update() may occur within one or more frames, but it is
        non-deterministic.

        The typical flow happens like this: the application draws to the OSD
        using a higher level canvas API.  When finished, it then waits for
        osd_can_update() to return True.  The canvas then renders the updates
        to the shared memory buffer (passed in 'osd_configure' signal, see
        below) and returns a list of regions that were updated.  osd_update()
        is then called, providing the list of regions in invalid_regions.  The
        alpha and visible parameters can optionally be passed at this time as
        well.

        It is only ever necessary to check osd_can_update() when you intend to
        pass invalid_regions to osd_update().  If you just want to update the
        alpha or visibiliy, you can call osd_update() at any time.

        The shared memory address for the OSD buffer is passed via the
        'osd_configure' signal.  Callbacks that connect to this signal will
        receive 5 arguments: width, height, buffer_addr, buffer_width,
        buffer_height.

            width, height:
                Indicates the size of the OSD, which is probably the size of
                the video.  This is the drawable area for the OSD overlay.

            buffer_addr:
                The address to the shared memory buffer.  Pixels are in BGRA
                format.  Note that although this is refered to as a buffer,
                it's an integer value representing memory address of the
                buffer, not a Python buffer object.

            buffer_width, buffer_height:
                Indicates the size of the OSD buffer.  The buffer pointed to
                by buffer_addr is at least buffer_width*buffer_height*4 bytes
                in size.  The rowstride of the image is buffer_width*4.

        This signal is typically emitted as soon as the resolution of the video
        is known.

        """
        if self._player:
            return self._player.osd_update(alpha, visible, invalid_regions)


    # For CAP_CANVAS

    def set_frame_output_mode(self, vo = None, notify = None, size = None):
        """
        Controls if and how frames are delivered via the 'frame' signal, and
        whether or not frames are drawn to the vo driver's video window.

            vo:
                If True, video will be passed to the player's vo driver for
                rendering (as is the case during normal operation).  If False,
                video will be suppressed.

            notify:
                If True, each time the player is about to draw a new video
                frame, a 'frame' signal is emitted with the particulars (see
                below).

            size:
                A 2-tuple of (width, height) that specifies the desired target
                size of the frame as provided to callbacks connected to the
                'frame' signal.  It's not guaranteed that the frame size will
                be this size, so consider this only a "serving suggestion."
                This does not affect the video rendered to the vo driver's
                output.

        If any of these parameters are None, their state will not be altered.
     
        When notify is True, the 'frame' signal will be emitted for every new
        frame.  Callbacks connected to this signal will receive 5 argments:
        width, height, aspect, buffer_addr, format.  
        
            width, height:
                Width and height specify the size of the frame.  Note that this
                size may not be the size that was passed to the last call to
                set_frame_output_mode() (perhaps the player's scaler couldn't
                scale to the requested size, or the frame was deposited before
                the resize request was received.)  

            aspect:
                A float specifying the aspect ratio of the given frame.

            buffer_addr:
                The memory address containing frame data.  The format of this
                data depends on the format parameter.  Note that although this
                is refered to as a buffer, it's an integer value representing
                memory address of the buffer, not a Python buffer object.

            format:
                A string specifying the format of the frame.  Supported formats
                are "yv12" or "bgr32".  If bgr32, the buffer pointed to by
                'buffer_addr' will be width*height*4 in size and pixels will be
                in BGR32 format.  If yv12, frame is in planar format, where
                each plane is stored contiguously in memory.  The buffer size
                will be width*height*2, and planes are stored in YCrCb order.

        After handling a frame delivered by the frame signal, you must call
        unlock_frame_buffer().
        """
        # TODO: ability to specify colorspace of frame.
        if self._player:
            return self._player.set_frame_output_mode()


    def unlock_frame_buffer(self):
        """
        Unlocks the frame buffer provided by the last 'frame' signal

        When a frame is delivered via the frame signal, its buffer is locked,
        preventing the player from writing a new frame to the buffer, giving
        you the opportunity to process the frame without the risk that it gets
        munged.  When you're done with the frame buffer, call this function.

        Failure to call this function will cause the player to drop frames.
        Audio may stutter, depending on how gracefully the player handles this
        delay.
        """
        if self._player:
            return self._player.unlock_frame_buffer()
