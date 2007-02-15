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
import logging

# kaa imports
import kaa.notifier
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
    and in the correct order of all pending calls.
    """
    def decorator(func):

        def newfunc(self, *args, **kwargs):
            if self._get_state() in states and not self._pending:
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

            # fit method. One of 'bars', 'scale', 'zoom'
            'fit-method': config.video.fit_method,

            # pre-caching, use 'auto' for defaults based on filetype / schema
            'cache' : 'auto'
        }

        self.signals = {

            # signals created by this class
            "open": kaa.notifier.Signal(),
            "start": kaa.notifier.Signal(),
            "play": kaa.notifier.Signal(),
            "end": kaa.notifier.Signal(),
            "failed": kaa.notifier.Signal(),
            "pause": kaa.notifier.Signal(),
            "pause_toggle": kaa.notifier.Signal(),

            # "seek": kaa.notifier.Signal(),
            # Process died (shared memory will go away)
            # "shm_quit": kaa.notifier.Signal()

            # pass thru signals from player
            "elapsed": kaa.notifier.Signal(),
            "stream_changed": kaa.notifier.Signal(),
            # Emitted when a new frame is availabnle.  See
            # set_frame_output_mode() doc for more info.
            "frame": kaa.notifier.Signal(), # CAP_CANVAS
            # Emitted when OSD buffer has changed.  See osd_update() doc
            # for more info.
            "osd_configure": kaa.notifier.Signal(),  # CAP_OSD
        }

        # pending commands
        self._pending = []
        self._blocked = False
        self._failed_player = []


    def set_window(self, window):
        if window:
            self._size = window.get_size()
        self._window = window
        if self._player:
            self._player.set_window(self._window)
            self._player.set_size(self._size)


    def _get_player_class(self, player=None):
        """
        Return player class object to play the current mrl. This function
        uses self._media, self._open_caps as mrl and caps and respects
        the failed player and the player deactived in the config. If player
        is given as argument, this player will be used.
        """
        exclude = self._failed_player[:]
        for p in backends.manager.get_all_players():
            if not getattr(config, p).activate and not p in exclude:
                exclude.append(p)
        return backends.manager.get_player_class(\
            self._media, self._open_caps, exclude, player, self._window)


    def _state_change(self, old_state, state):
        """
        """
        log.debug('%s %s -> %s', str(self._player)[1:-1], old_state, state)

        if old_state in (STATE_OPENING, STATE_OPEN) and \
               state in (STATE_IDLE, STATE_NOT_RUNNING, STATE_SHUTDOWN):
            # From STATE_OPEN(ING) to not playing. This means something
            # went wrong and the player failed to play.  This means
            # that the player we wanted to use was unable to play this
            # file. In that case we add the player the list of of
            # failed_player and try to find a better one.
            # TODO: What happens if the user tries to open a new file
            # while we are trying to find a good player for the old
            # mrl?
            self._failed_player.append(self.get_player_id())
            # FIXME: why is this here? If we delete our pending functions
            # a 'play' after open may get missed. So let's see what happens
            # if we don't delete the pending calls here :)
            # self._pending = []
            self._player.release()
            cls = self._get_player_class()
            if cls:
                # a new possible player is found, try it
                # remove all pending information to make it possible to call
                # create and open now. After that, add them again.
                pending = self._pending
                self._pending = []
                self._create_player(cls, True)
                self._open()
                if old_state == STATE_OPEN:
                    self.play()
                self._pending.extend(pending)
                return True
            # everything failed
            self.signals["failed"].emit()

        if old_state == STATE_OPENING and state == STATE_OPEN:
            # stream open now for playing
            self.signals["open"].emit(self._player.get_info())

        if old_state == STATE_OPEN and \
               state in (STATE_PLAYING, STATE_PAUSED):
            # From STATE_OPENING to playing. Signal playback start
            self.signals["start"].emit()
            self.signals["play"].emit()

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

        if state == STATE_NOT_RUNNING == self._player.get_state() and \
               not self._pending:
            # Player released the video and audio device. Right now we set
            # self._player to None to simulate STATE_NOT_RUNNING.
            # This needs to be fixed.
            self._player = None

        if self._get_state() == STATE_IDLE and not self._pending and \
               not old_state == STATE_NOT_RUNNING:
            # no new mrl to play, release player
            log.info('release player')
            return self._player.release()

        # Handle pending calls based on the new state. The variable blocked is
        # used to avoid calling this function recursive.
        if self._blocked or kaa.notifier.shutting_down:
            return
        self._blocked = True
        # Iterate through all pending commands and execute the ones that can
        # be called in our new state.
        for states, callback in self._pending[:]:
            if self._get_state() in states:
                callback()
                self._pending.remove((states, callback))
        self._blocked = False


    @required_states(STATE_NOT_RUNNING)
    def _create_player(self, cls, copy_properties=False):
        """
        Create a player based on cls.
        """
        properties = self._properties
        if copy_properties and self._player:
            properties = self._player._properties
            for key, value in self._player._property_delayed:
                properties[key] = value
            self._player._property_delayed = []
        properties = properties.copy()

        self._player = cls(properties)
        self._player._state_changed.connect_weak(self._state_change)
        for signal in self._player.signals:
            self._player.signals[signal].connect_weak(self.signals[signal].emit)


    @required_states(STATE_NOT_RUNNING, STATE_IDLE)
    def _open(self):
        """
        The real open function called from 'open'.
        """
        self._player.set_window(self._window)
        self._player.set_size(self._size)
        # FIXME: maybe give the whole media object to the child
        self._player.open(self._media)


    # Player API

    def open(self, mrl, caps = None, player = None):
        """
        Open mrl. The parameter 'caps' defines the needed capabilities the
        player must have. If 'player' is given, force playback with the
        given player.
        """
        if kaa.notifier.shutting_down:
            return False

        self._media = kaa.metadata.parse(mrl)
        if not self._media:
            # unable to detect, create dummy
            if mrl.find('://') == -1:
                mrl = 'file://%s'
            self._media = kaa.metadata.Media(hash=dict(url=mrl, media='MEDIA_UNKNOWN'))
        self._media.scheme = self._media.url[:self._media.url.find(':/')]

        self._open_caps = caps
        self._failed_player = []
        cls = self._get_player_class(player)

        if not cls:
            raise PlayerError("No supported player found to play %s", mrl)

        self._pending = []
        if not self._player:
            self._create_player(cls)
        else:
            if self._get_state() not in (STATE_IDLE, STATE_NOT_RUNNING,
                                         STATE_SHUTDOWN, STATE_STOPPING):
                self._player.stop()
            if not isinstance(self._player, cls):
                self._player.release()
                self._create_player(cls)
            else:
                self._player._properties = self._properties.copy()
        self._open()


    @required_states(STATE_OPEN, STATE_PLAYING, STATE_PAUSED)
    def play(self):
        if self.get_state() in (STATE_PLAYING, STATE_PAUSED):
            # called to toggle play/pause
            log.info('resume playback')
            self._player.resume()
        else:
            log.info('start playback')
            self._player.play()


    @required_states(STATE_PLAYING, STATE_PAUSED, STATE_STOPPING)
    def stop(self):
        """
        Stop playback.
        """
        if self._get_state() == STATE_STOPPING:
            # ignore this stop() call
            return
        # FIXME: handle player that are in a deadlock and do not
        # want to be killed.
        self._player.stop()


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def pause(self):
        """
        Pause playback.
        """
        if self.get_state() == STATE_PLAYING:
            self._player.pause()


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def resume(self):
        """
        Resume playback.
        """
        if self.get_state() == STATE_PAUSED:
            self._player.resume()


    @required_states(STATE_PLAYING, STATE_PAUSED)
    def pause_toggle(self):
        """
        Toggle play / pause.
        """
        if self.get_state() == STATE_PLAYING:
            self._player.pause()
        else:
            self._player.resume()


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
