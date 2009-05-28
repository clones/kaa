# -*- coding: iso-8859-1 -*-
# $Id$
# -----------------------------------------------------------------------------
# player.py - Generic player interface proxying the backends
# -----------------------------------------------------------------------------
# kaa.popcorn - Generic Player API
# Copyright (C) 2008 Jason Tackaberry, Dirk Meyer
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
# -----------------------------------------------------------------------------

__all__ = ['Player']

# python imports
import logging

# kaa imports
import kaa
import kaa.metadata
from kaa.weakref import weakref
from kaa.utils import property

# kaa.popcorn imports
from backends import manager
from common import *
from config import config

# get logging object
log = logging.getLogger('popcorn')


class StreamProperties(object):
    def __init__(self, player):
        self._player = weakref(player)


    def _check_prop(self, prop):
        """
        Ensures the backend has the given property.  A special case is made for
        the 'state' property, which backends do have, but we don't expose it
        to the caller because it is settable.
        """
        if prop == 'state' or \
           getattr(self._player._backend.__class__, prop, None).__class__.__name__ != 'property':
            raise AttributeError('Stream does not have property: %s' % prop)


    def __getattr__(self, attr):
        if attr.startswith('_'):
            return super(StreamProperties, self).__getattr__(attr)
        self._check_prop(attr)
        return getattr(self._player._backend, attr)


    def __setattr__(self, attr, value):
        if attr.startswith('_'):
            return super(StreamProperties, self).__setattr__(attr, value)
        self._check_prop(attr)
        return setattr(self._player._backend, attr, value)



class Player(kaa.Object):
    """
    Generic Player class provides a unified interface for multiple backends.
    Anything not explicitly handled by the generic player is proxied directly
    to the backend, allowing for backend-specific extensions to be accessed.
    """
    __kaasignals__ = {
        'open':
            '''
            Emitted when a new stream is successfully opened.

            .. describe:: def callback(media, ...)

            Before callbacks are invoked, player state becomes STATE_OPEN.

            Once this signal is emitted, several stream properties are
            available, as well as the media property.  However, do not rely on
            frame size or aspect here, use the 'start' signal for that.
            ''',

        'start':
            '''
            Emitted once the stream has started playing just after being opened.

            .. describe:: def callback(...)

            Before callbacks are invoked, player state becomes STATE_PLAYING.

            Only emitted once when the stream starts after STATE_OPEN, and not
            after STATE_PAUSED.  When this signal fires, the backend's decoder
            has started, and so any decoder-discovered properties are known
            (frame width, height, and especially aspect ratio).  Do not rely on
            those properties before this signal (such as in the open signal).

            The reason is that, for example, correct aspect ratio may be stored
            in the frame header which is not known at time of open.  Think of
            the 'open' signal at the demuxer level, and 'start' at the decoder
            level.
            ''',

        'play':
            '''
            Emitted when the stream begins playing, after having been either
            opened or paused.

            .. describe:: def callback(...)

            Before callbacks are invoked, player state becomes STATE_PLAYING.

            This signal will emit after a transition to STATE_PLAYING from
            either STATE_OPEN or STATE_PAUSED.  For the initial play, the
            ``start`` signal will emit before ``play``.
            ''',

        'finished':
            '''
            Emitted when the stream finishes playing to either completion or
            due to error.

            .. describe:: def callback(...)

            Before callbacks are invoked, player state becomes either STATE_IDLE
            or STATE_NOT_RUNNING, depending on the backend.

            This signal will not be emitted when the stream is stopped through
            an API call (either explicitly via stop(), or implicitly by calling
            open() on a different file).  It will also be emitted when the
            backend experiences an error and aborts the stream.  This signal
            therefore emits an error argument, which is None if the stream
            finished properly, and an exception object (whose message property
            is human-readable) otherwise.

            One use-case for this signal is to implement a playlist.  When the
            signal emits, it would be appropriate to advance to the next file
            in the playlist.
            ''',

        'stop':
            '''
            Emitted when the stream is explicitly stopped by a call to
            :meth:`~kaa.popcorn.Player.stop`.

            .. describe:: def callback(...)

            Before callbacks are invoked, player state becomes either STATE_IDLE
            or STATE_NOT_RUNNING, depending on the backend.
            ''',

        'seek':
            '''
            Emitted when the position in the stream is changed by a call to
            :meth:`~kaa.popcorn.Player.seek`.

            .. describe:: def callback(oldpos, newpos, ...)

               :param oldpos: position in stream before the seek
               :type oldpos: float
               :param newpos: position in stream after the seek
               :type newpos: float
            ''',

        'position-changed':
            '''
            Emitted periodically as the position in the stream changes.

            .. describe:: def callback(oldpos, newpos, ...)

               :param oldpos: position in stream before the seek
               :type oldpos: float
               :param newpos: position in stream after the seek
               :type newpos: float

            This signal differs from seek in that it is also called
            periodically as the stream position progresses during play.  The
            interval varies by backend, but will not be greater than 500ms.  If
            :meth:`~kaa.popcorn.Player.seek` was called, this signal will be
            emitted after the :attr:`~kaa.popcorn.Player.signals.seek` signal.
            ''',

        'error':
            '''
            A catch-all error signal, emitted upon any error with the player.

            .. describe:: def callback(exc, oldstate, newstate, ...)

               :param exc: an exception object for the error
               :param oldstate: the player state prior to the error
               :param newstate: the player state after the error

            It is not defined whether or not the new state has been applied
            when this signal emits.

            In general this signal should not be needed, as exceptions will be
            passed through InProgress objects and it's preferrable they are
            handled that way.
            ''',

        'pause':
            '''
            Emitted when the stream pauses after having been playing.

            .. describe:: def callback(...)

            Before callbacks are invoked, player state becomes STATE_PAUSED.
            ''',

        'pause-toggle':
            '''
            Emitted when the state toggles between the playing and paused states.

            .. describe:: def callback(...)

            Before callbacks are invoked, player state becomes STATE_PAUSED
            if state was STATE_PLAYING, and STATE_PLAYING if state was
            STATE_PAUSED.
            ''',

        'stream-changed':
            '''
            Emitted when one or more attributes of the stream have changed
            during playback.

            .. describe:: def callback(...)

            Some stream attributes, such as frame size, aspect ratio, number of
            available audio streams, etc, are dynamic and can change while the
            stream is playing.  This emits regularly during DVD playback, such
            as for example moving from video to DVD menu, or progressing
            naturally through titles (e.g. previews to FBI disclaimer to
            feature title).

            This signal will also emit when the stream begins.
            '''
    }

    def __init__(self, window=None):
        super(Player, self).__init__()
        # Backend instance currently in use.  This is assigned in open()
        self._backend = None
        self._window = window
        # kaa.metadata Media object for the currently opened mrl.
        self._media = None
        self._stream = StreamProperties(self)

        # If not None, is an InProgress object 
        self._open_inprogress = None
        self._finished_inprogress = kaa.InProgress()

        # Properties that apply to all streams when they first open.  When
        # they are set to None, the value from config is used.  Otherwise
        # they are user-specified values that override config.
        self._prop_deinterlace = None
        self._prop_cache = None
        self._prop_audio_delay = None


    #########################################
    # Properties

    @property
    def media(self):
        return self._media


    @property
    def state(self):
        if not self._backend:
            return STATE_NOT_RUNNING
        return self._backend._state

    @property
    def opened(self):
        return self._backend and self._backend._state == STATE_OPEN

    @property
    def playing(self):
        return self._backend and self._backend._state == STATE_PLAYING

    @property
    def stopped(self):
        return not self._backend or self._backend._state in (STATE_NOT_RUNNING, STATE_IDLE)

    @property
    def stream(self):
        """
        Namespace for stream-specific properties.
        """
        if not self._backend:
            return None
        return self._stream

    @property
    def backend(self):
        """
        Returns the name of the backend (not the backend itself).
        """
        if not self._backend:
            return None
        return self._backend.__class__._player_id

    @property
    def capabilities(self):
        if not self._backend:
            return ()
        return self._backend._player_caps


    @property
    def deinterlace(self):
        # TODO: define different generic deinterlacing modes.
        return 'auto' if self._prop_deinterlace is None else self._prop_deinterlace

    @deinterlace.setter
    def deinterlace(self, value):
        self._prop_deinterlace = value


    @property
    def cache(self):
        return 'auto' if self._prop_cache is None else self._prop_cache

    @cache.setter
    def cache(self, value):
        self._prop_cache = value


    @property
    def audio_delay(self):
        return config.audio.delay if self._prop_audio_delay is None else self._prop_audio_delay

    @audio_delay.setter
    def audio_delay(self, value):
        self._prop_audio_delay = value


    #########################################
    # Methods

    def __inprogress__(self):
        return self._finished_inprogress

        
    def __getattr__(self, attr):
        # Proxy anything not in our namespace to the backend.  Allows for
        # backend-specific extensions.  If the backend does not have the
        # requested attr or it isn't callable, raises an exception.
        backend = object.__getattribute__(self, '_backend')
        if backend:
            try:
                return object.__getattribute__(self, attr)
            except AttributeError:
                val = backend.__getattribute__(attr)
                if callable(val):
                    return val
        return object.__getattribute__(self, attr)


    def _emit_finished(self, exc):
        self.signals['finished'].emit(exc)
        if exc is None:
            self._finished_inprogress.finish(None)
        else:
            self._finished_inprogress.throw(type(exc), exc, None)

        # Create new InProgress for next stream. 
        self._finished_inprogress = kaa.InProgress()


    @kaa.coroutine()
    def open(self, mrl, caps=None, player=None):
        if kaa.main.is_shutting_down():
            yield False

        if self._open_inprogress:
            yield self.stop()

        media = kaa.metadata.parse(mrl)
        if not media:
            # unable to detect, create dummy media object.
            if '://' not in mrl:
                mrl = 'file://' + mrl
            media = kaa.metadata.Media(hash=dict(url=mrl, media='MEDIA_UNKNOWN'))
        media.scheme = media.url[:media.url.find(':/')]

        try:
            self._open_inprogress = self._open(media, caps, player)
            yield self._open_inprogress
            self.signals['open'].emit(media)
        finally:
            self._open_inprogress = None


    @kaa.coroutine()
    def _open(self, media, caps, player):
        if self._window and CAP_VIDEO not in caps:
            caps = tuple(caps) + (CAP_VIDEO,)

        # TODO: iterate through available players, keeping track of failed.
        cls = manager.get_player_class(media, caps, [], player)
        log.info('Chose backend %s for mrl %s', cls._player_id, media.url)
        if self._backend:
            # We already have a backend. The backend has to be stopped if
            # it is running and has to release all resources if it is
            # not the player we choose next.
            yield self._backend.stop()
            if cls and not isinstance(self._backend, cls):
                # We selected a different backend, so the current backend must
                # release all resources.
                yield self._backend.release()
                self._backend = None

        if not cls:
            # No viable player found.
            error = PlayerError('No viable player found to play %s' % media.url)
            self.signals['error'].emit(error, self.state, self.state)
            raise error

        if self._backend:
            # Reuse current backend with new mrl.
            self._backend.reset()
        else:
            # Create a new player of the given cls.
            self._backend = cls(self)

        self._media = media
        self._backend.window = self._window
        yield self._backend.open(self.media)


    @kaa.coroutine()
    def stop(self):
        if self._open_inprogress:
            # We've aborted an in-progress open().  Finish it with an
            # exception to wakeup anything waiting on it.
            self._open_inprogress.abort(PlayerAbortedError('Open aborted'))
            self._open_inprogress = None

        if self._backend:
            yield self._backend.stop()


    @precondition(backend=True)
    def play(self):
        if self.state == STATE_PAUSED:
            return self._backend.resume()
        return self._backend.play()


    @precondition(backend=True)
    def pause(self):
        return self._backend.pause()


    @precondition(backend=True)
    def pause_toggle(self):
        if self.state == STATE_PLAYING:
            return self._backend.pause()
        return self._backend.resume()
    

    @precondition(backend=True)
    def resume(self):
        return self._backend.resume()


    @precondition(backend=True)
    def seek(self, value, type=SEEK_RELATIVE):
        """
        Should be possible to seek on open.
        """
        return self._backend.seek(value, type)


    @precondition(backend=True)
    def nav(self, input):
        if CAP_DVD_MENUS not in self.capabilities:
            raise PlayerError('Current backend (%s) does not support DVD menus')
        return self._backend.nav(input)
