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
import os
import sys
import logging

# kaa imports
import kaa
import kaa.metadata

# kaa.popcorn imports
import backends.manager
from config import config
from ptypes import *

# get logging object
log = logging.getLogger('popcorn')


def required_states(*states):
    """
    Decorator to make sure a function is only called in the corrent state
    and in the correct order of all pending calls. A function decorated
    with this decorator always returns an InProgress object.
    """
    def decorator(func):

        def newfunc(self, *args, **kwargs):
            # always return an InProgress object and handle the
            # function like it is decorated with coroutine
            afunc = kaa.coroutine()(func)
            async = kaa.InProgress()
            if self._get_state() in states and not self._pending:
                # already finished
                async.finished(afunc(self, *args, **kwargs))
            else:
                # add callback to list of pending calls
                callback = kaa.Callback(afunc, self, *args, **kwargs)
                self._pending.append((states, async, callback))
            return async
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
    def __init__(self, window=None):

        self._player = None
        self._media = None
        self._size = (0,0)
        self.set_window(window)

        self._properties = {

            # If a property is changed when no uri is loaded
            # it will affect all uris loaded after this point.
            # If changed when an uri is loaded it will only
            # affect this one. Some properties can not be
            # changed after the stream is started because the
            # backend does not support it.

            # settings that are set global is most cases
            'postprocessing': config.video.postprocessing,
            'software-scaler': config.video.software_scaler,

            # settings usefull for changing after a stream is
            # loaded.
            'deinterlace': 'auto',
            'audio-track': None,
            'audio-filename': None,
            'subtitle-track': None,
            'subtitle-filename': None,

            # Sets the audio delay relative to the video.  A positive
            # value causes audio to come later, while a negative value
            # plays the audio before.
            'audio-delay': 0.0,

            # scale method. One of SCALE_METHODS
            'scale': SCALE_KEEP,

            # zoom into the movie
            'zoom': 100,
            
            # pre-caching, use 'auto' for defaults based on filetype / schema
            'cache' : 'auto'
        }

        self.signals = {

            # signals created by this class
            "open": kaa.Signal(),
            "start": kaa.Signal(),
            "play": kaa.Signal(),
            "end": kaa.Signal(),
            "failed": kaa.Signal(),
            "pause": kaa.Signal(),
            "pause_toggle": kaa.Signal(),

            # "seek": kaa.Signal(),
            # Process died (shared memory will go away)
            # "shm_quit": kaa.Signal()

            # pass thru signals from player
            "elapsed": kaa.Signal(),
            "stream_changed": kaa.Signal(),
            # Emitted when a new frame is availabnle.  See
            # set_frame_output_mode() doc for more info.
            "frame": kaa.Signal(), # CAP_CANVAS
            # Emitted when OSD buffer has changed.  See osd_update() doc
            # for more info.
            "osd_configure": kaa.Signal(),  # CAP_OSD
        }

        # pending commands
        self._pending = []
        # waiting InProgress objects
        self._waiting = []
        self._blocked = False
        self._failed_player = []


    def set_window(self, window):
        if window:
            self._size = window.get_size()
        self._window = window
        if self._player:
            self._player.set_window(self._window)
            self._player.set_size(self._size)


    def _state_change(self, old_state, state):
        """
        """
        log.info('%s %s -> %s', str(self._player)[1:-1], old_state, state)

        for wait, states in self._waiting[:]:
            if state in states:
                wait.finished(self._waiting.remove((wait, states)))

        if old_state in (STATE_PLAYING, STATE_PAUSED, STATE_STOPPING) and \
               state in (STATE_IDLE, STATE_NOT_RUNNING, STATE_SHUTDOWN):
            # From playing to finished. Signal end.
            self.signals["end"].emit()

        if old_state == STATE_PLAYING and state == STATE_PAUSED:
            self.signals["pause"].emit()
            self.signals["pause_toggle"].emit()

        if old_state == STATE_PAUSED and state == STATE_PLAYING:
            self.signals["play"].emit()
            self.signals["pause_toggle"].emit()

        if self._get_state() == STATE_IDLE and not self._pending and \
               not old_state == STATE_NOT_RUNNING:
            # no new mrl to play, release player
            log.info('release player')
            return self._player.release()

        # Handle pending calls based on the new state. The variable blocked is
        # used to avoid calling this function recursive.
        if self._blocked or kaa.main.is_shutting_down():
            return
        self._blocked = True
        # Iterate through all pending commands and execute the ones that can
        # be called in our new state.
        for states, async, callback in self._pending[:]:
            if self._get_state() in states:
                try:
                    async.finished(callback())
                except Exception, e:
                    async.throw(*sys.exc_info())
                self._pending.remove((states, async, callback))
        self._blocked = False


    def wait(self, *states):
        """
        Return InProgress object that will be finished when one of the
        given states is reached.
        """
        async = kaa.InProgress()
        if self._get_state() in states:
            # already in a state we want
            async.finished(True)
            return async
        # append to the list of waiting InProgress signals
        self._waiting.append((async, states))
        return async


    @kaa.coroutine()
    def _open(self, player=None):
        """
        The real open function called from 'open' and 'play'. This function
        will try to open the current url. At the end of this function the
        internal state is either STATE_OPEN or an error is raised.
        """
        # use the exclude list and the given player to get a
        # player class to start
        exclude = self._failed_player[:]
        for p in backends.manager.get_all_players():
            if not getattr(config, p).enabled and not p in exclude:
                exclude.append(p)
        cls = backends.manager.get_player_class(\
        self._media, self._open_caps, exclude, player, self._window)

        if self._player:
            # We already have a player. The player has to be stopped if
            # it is running and has to release all resources if it is
            # not the player we choose next.
            if self._get_state() not in (STATE_IDLE, STATE_NOT_RUNNING,
                                         STATE_SHUTDOWN, STATE_STOPPING):
                # player is running, stop it
                self._player.stop()
                yield self.wait(STATE_IDLE, STATE_NOT_RUNNING)
            if not cls or not isinstance(self._player, cls):
                # wrong player, release resources
                self._player.release()
                yield self.wait(STATE_NOT_RUNNING)
                self._player = None

        if not cls:
            # No possible player.
            self.signals["failed"].emit()
            raise PlayerError("No supported player found to play %s", self._media.url)

        if self._player:
            # Reuse player
            self._player._properties = self._properties.copy()
        else:
            # Create a player based on cls.
            properties = self._properties.copy()
            self._player = cls(properties)
            self._player._state_changed.connect_weak(self._state_change)
            for signal in self._player.signals:
                self._player.signals[signal].connect_weak(self.signals[signal].emit)

        # set some player variables
        self._player.set_window(self._window)
        self._player.set_size(self._size)
        self._player.open(self._media)

        # wait until we reach STATE_OPEN (ready to play) or
        # STATE_IDLE or STATE_NOT_RUNNING (failed)
        yield self.wait(STATE_OPEN, STATE_IDLE, STATE_NOT_RUNNING)
        if self._get_state() == STATE_IDLE:
            # Player is idle. This means it was not possible to open
            # the url. Release all resources.
            self._player.release()
        if self._get_state() in (STATE_IDLE, STATE_SHUTDOWN):
            # Wait until the not working player is stopped.
            yield self.wait(STATE_NOT_RUNNING)
        if self._get_state() == STATE_NOT_RUNNING:
            # Try next player if no specific player was given
            if player:
                self.signals["failed"].emit()
                raise PlayerError("Forced player %s does not work", player)
            self._failed_player.append(self.get_player_id())
            yield self._open()



    # Player API

    @kaa.coroutine()
    def open(self, mrl, caps = None, player = None):
        """
        Open mrl. The parameter 'caps' defines the needed capabilities the
        player must have. If 'player' is given, force playback with the
        given player.
        """
        if kaa.main.is_shutting_down():
            yield False

        self._media = kaa.metadata.parse(mrl)
        if not self._media:
            # unable to detect, create dummy
            if '://' not in mrl:
                mrl = 'file://' + mrl
            self._media = kaa.metadata.Media(hash=dict(url=mrl, media='MEDIA_UNKNOWN'))
        self._media.scheme = self._media.url[:self._media.url.find(':/')]

        self._open_caps = caps
        self._failed_player = []
        self._pending = []
        yield self._open(player)
        self.signals['open'].emit(self._player.get_info())

        
    @required_states(STATE_OPEN, STATE_PLAYING, STATE_PAUSED)
    def play(self):
        """
        Start or resume playback. Returns an InProgress object.
        """
        if self.get_state() in (STATE_PLAYING, STATE_PAUSED):
            # called to toggle play/pause
            log.info('resume playback')
            self._player.resume()
            yield self.wait(STATE_PLAYING)
            return
        log.info('start playback')
        self._player.play()
        yield self.wait(STATE_PLAYING, STATE_NOT_RUNNING, STATE_IDLE)
        if self._get_state() == STATE_PLAYING:
            return
        self._failed_player.append(self.get_player_id())
        yield self._open()
        yield self.play()
        self.signals["start"].emit()
        self.signals["play"].emit()


    @required_states(STATE_PLAYING, STATE_PAUSED, STATE_STOPPING)
    def stop(self):
        """
        Stop playback. Returns an InProgress object.
        """
        if self._get_state() != STATE_STOPPING:
            # FIXME: handle player that are in a deadlock and do not
            # want to be killed.
            self._player.stop()
        return self.wait(STATE_NOT_RUNNING, STATE_IDLE)


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def pause(self):
        """
        Pause playback. Returns an InProgress object.
        """
        if self.get_state() == STATE_PAUSED:
            return
        self._player.pause()
        yield self.wait(STATE_PAUSED)
        

    @required_states(STATE_PLAYING, STATE_PAUSED)
    def resume(self):
        """
        Resume playback. Returns an InProgress object.
        """
        if self.get_state() == STATE_PLAYING:
            return
        self._player.resume()
        yield self.wait(STATE_PLAYING)


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def pause_toggle(self):
        """
        Toggle play / pause. Returns an InProgress object.
        """
        if self.get_state() == STATE_PLAYING:
            return self.pause()
        return self.resume()


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def seek(self, value, type=SEEK_RELATIVE):
        """
        Seek. Possible types are SEEK_RELATIVE, SEEK_ABSOLUTE and SEEK_PERCENTAGE.
        """
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
        # FIXME: more sure the following variables can be accessed:
        # audio-track-list, subtitle-track-list, elapsed and length
        if self._player:
            return self._player.get_info()
        return {}


    def get_media(self):
        """
        Return kaa.metadata media object of the mrl loaded.
        """
        return self._media


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


    def _get_state(self):
        """
        Get state of the player for internal use.
        """
        if not self._player:
            return STATE_NOT_RUNNING
        return self._player.get_state()


    def get_state(self):
        """
        Get state of the player. Note: STATE_NOT_RUNNING is for internal use.
        This function will return STATE_IDLE if the player is not running.
        """
        if not self._player:
            return STATE_IDLE
        if self._player.get_state() in (STATE_NOT_RUNNING, STATE_SHUTDOWN):
            return STATE_IDLE
        return self._player.get_state()


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


    def set_property(self, prop, value):
        """
        Set a property to a new value. If an url is open right now, this
        will only affect the current url.
        """
        # FIXME: use pending for some properties to respect the state.
        # E.g. user calls open();play();set_property() the set_property
        # should be handled in STATE_PLAYING.
        if self._player:
            return self._player.set_property(prop, value)
        self._properties[prop] = value


    def get_property(self, prop):
        """
        Get property value.
        """
        if self._player:
            return self._player._properties.get(prop)
        return self._properties.get(prop)


    def properties(self):
        """
        Return a list of all known properties.
        """
        if self._player:
            return self._player._properties.keys()
        return self._properties.keys()


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

    @required_states(STATE_IDLE, STATE_OPENING, STATE_OPEN, STATE_PLAYING, STATE_PAUSED)
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
            return self._player.set_frame_output_mode(vo, notify, size)


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


    def get_capabilities(self):
        """
        Return player capabilities.
        """
        if not self._player:
            return ()
        return self._player.get_capabilities()


    def has_capability(self, cap):
        """
        Return if the player has the given capability.
        """
        if not self._player:
            return False
        return self._player.has_capability(cap)
