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

all = [ 'Player' ]

# python imports
import logging

# kaa imports
import kaa.notifier

# kaa.popcorn imports
from config import config as default_config
from ptypes import *
from backends.manager import get_player_class, get_all_players

# get logging object
log = logging.getLogger('popcorn')

def required_states(*states):
    """
    Decorator to make sure a function is only called in the corrent state
    and in the correct order of all pending calls.
    """
    def decorator(func):

        def newfunc(self, *args, **kwargs):
            if self.get_state() in states and not self._pending:
                return func(self, *args, **kwargs)
            # print 'pending:', func, self.get_state(), states
            callback = kaa.notifier.Callback(func, self, *args, **kwargs)
            self._pending.append((states, callback))
            
        try:
            newfunc.func_name = func.func_name
        except TypeError:
            pass
        newfunc.states = states
        return newfunc

    return decorator


class Player(object):
    """
    Generic player. On object of this class will use the players from the
    backend subdirectory for playback.
    """
    def __init__(self, window=None, config=default_config):

        self._player = None
        self._size = (0,0)
        if window:
            self._size = window.get_size()
        self._window = window
        self._config = config
        
        self.signals = {

            # signals created by this class
            "open": kaa.notifier.Signal(),
            "start": kaa.notifier.Signal(),
            "failed": kaa.notifier.Signal(),
            "end": kaa.notifier.Signal(),

            # pass thru signals from player
            "pause": kaa.notifier.Signal(),
            "play": kaa.notifier.Signal(),
            "pause_toggle": kaa.notifier.Signal(),
            "seek": kaa.notifier.Signal(),
            "stream_changed": kaa.notifier.Signal(),
            # Emitted when a new frame is availabnle.  See 
            # set_frame_output_mode() doc for more info.
            "frame": kaa.notifier.Signal(), # CAP_CANVAS
            # Emitted when OSD buffer has changed.  See osd_update() doc
            # for more info.
            "osd_configure": kaa.notifier.Signal(),  # CAP_OSD
            # Process died (shared memory will go away)
            "shm_quit": kaa.notifier.Signal()
        }

        # pending commands
        self._pending = []
        self._blocked = False
        self._player = None
        self._failed_player = []
        

    def _state_change(self, signal):
        """
        The used player changed its state and emited a signal. This function
        will emit the same signal to the application, handles some internal
        changes and will call the pending calls based on the new state.
        """
        log.debug('player signal: %s', signal)
        
        if signal == 'failed':
            # The playing has failed. This means that the player we wanted to
            # use was unable to play this file. In that case we add the player
            # the list of of failed_player and try to find a better one.
            # TODO: What happens if the user tries to open a new file while
            # we are trying to find a good player for the old mrl?
            self._failed_player.append(self.get_player_id())
            self._pending = []
            self._player.release()
            cls = get_player_class(mrl = self._open_mrl, caps = self._open_caps,
                                   exclude = self._failed_player)
            if cls:
                # a new possible player is found, try it
                self._create_player(cls)
                self._open(self._open_mrl)
                self.play()
                return
            
        if signal in self.signals:
            # signal the change
            self.signals[signal].emit()

        if signal in ('end', 'failed') and self.get_state() == STATE_IDLE \
               and not self._pending:
            # no new mrl to play, release player
            log.info('release player')
            return self._player.release()

        if signal == 'release':
            # Player released the video and audio device. Right now we set
            # self._player to None to simulate STATE_NOT_RUNNING.
            # This needs to be fixed.
            self._player = None

        # Handle pending calls based on the new state. The variable blocked is
        # used to avoid calling this function recursive.
        if self._blocked:
            return
        self._blocked = True
        while self._pending and self.get_state() in self._pending[0][0]:
            self._pending.pop(0)[1]()
        self._blocked = False


    @required_states(STATE_NOT_RUNNING)
    def _create_player(self, cls):
        """
        Create a player based on cls.
        """
        self._player = cls()
        for sig in self.signals:
            if sig in self._player.signals and \
                   not sig in ('start', 'failed', 'end'):
                self._player.signals[sig].connect_weak(self.signals[sig].emit)
        for sig in ('start', 'end', 'release', 'failed'):
            self._player.signals[sig].connect_weak(self._state_change, sig)

    
    @required_states(STATE_NOT_RUNNING, STATE_IDLE)
    def _open(self, mrl):
        """
        The real open function called from 'open'.
        """
        self._player.set_config(self._config)
        self._player.open(mrl)
        self._player.set_window(self._window)
        self._player.set_size(self._size)
        self.signals['open'].emit()


    # Player API

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

        self._pending = []
        self._failed_player = []
        if not self._player:
            self._create_player(cls)
        else:
            if not self._player.get_state() in (STATE_IDLE, STATE_NOT_RUNNING):
                self._player.stop()
            if not isinstance(self._player, cls):
                self._player.release()
                self._create_player(cls)
        self._open(mrl)


    @required_states(STATE_IDLE, STATE_PLAYING, STATE_PAUSED)
    def play(self):
        if self.get_state() in (STATE_PLAYING, STATE_PAUSED):
            # called to toggle play/pause
            log.info('resume playback')
            self._player.resume()
        else:
            log.info('start playback')
            self._player.play()


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def stop(self):
        """
        Stop playback.
        """
        # FIXME: handle player that are in a deadlock and do not
        # want to be killed.
        self._player.stop()


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def pause(self):
        """
        Pause playback.
        """
        self._player.pause()


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def resume(self):
        """
        Resume playback.
        """
        self._player.resume()


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def pause_toggle(self):
        """
        Toggle play / pause.
        """
        state = self.get_state()
        if state == STATE_PLAYING:
            self._player.pause()
        if state == STATE_PAUSED:
            self._player.resume()


    @required_states(STATE_IDLE, STATE_PLAYING, STATE_PAUSED)
    def seek(self, value, type=SEEK_RELATIVE):
        """
        Seek. Possible types are SEEK_RELATIVE, SEEK_ABSOLUTE and SEEK_PERCENTAGE.
        """
        if self.get_state() == STATE_IDLE:
            # FIXME: make it possible to seek between open() and play() and
            # add STATE_IDLE to required_states.
            return False
        self._player.seek(value, type)


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
        if not self._player:
            return STATE_NOT_RUNNING
        if self._player.get_state() != STATE_NOT_RUNNING:
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
