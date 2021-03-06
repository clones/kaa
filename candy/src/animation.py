# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - Animation Core
# -----------------------------------------------------------------------------
# $Id$
#
# TODO: add function to loop an animation
#       add pause function
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008-2010 Dirk Meyer, Jason Tackaberry
#
# First Version: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

from __future__ import with_statement

__all__ = [ 'Animation', 'thread_enter', 'thread_leave', 'thread_locked' ]

# python imports
import time
import logging
import gobject
import threading
import _weakref

# kaa imports
import kaa
from kaa.utils import property

# kaa.candy imports
import config
from behaviour import create_alpha, create_behaviour

# get logging object
log = logging.getLogger('kaa.candy')

# signal to trigger redraw
signals = {
    'candy-update': kaa.Signal()
}

# lock to prevent animations from updating the stage while the
# mainloop is doing some major changes
_lock_lock  = threading.RLock()
_lock_count = 0

def thread_enter():
    """
    Lock the clutter thread from updating the gui from animations. This should
    be used when the mainthread does major changes to the stage and a playing
    animations could redraw the gui while the changes are not complete.
    """
    global _lock_count
    if _lock_count == 0:
        _lock_lock.acquire()
    _lock_count += 1

def thread_leave(force=False):
    """
    Release the clutter thread. This function will be called automaticly on
    each mainloop iteration when the thread is locked.
    """
    global _lock_count
    if force:
        _lock_count = 1
    _lock_count -= 1
    if _lock_count == 0:
        _lock_lock.release()

def thread_locked():
    """
    Return if the thread is locked
    """
    return _lock_count


class Animation(object):
    """
    Basic animation class.
    """

    # class variable to hold all running animations
    __animations = []
    # class variable if the timer is registered to gobject
    __active = False
    # member variable set to an InProgress while the animation is playing
    __inprogress = None

    def __init__(self, secs, alpha_func='inc', callback=None):
        """
        Create an animation with a runtime in secs and use the
        alpha_func for the behaviours.
        """
        self.current_frame_num = 0
        self.n_frames = int(float(secs) * config.fps)
        if isinstance(alpha_func, str):
            alpha_func = create_alpha(alpha_func)
        self.alpha_func = alpha_func
        self.behaviour = []
        self.__refs = []
        self.delay = 0
        self.callback = callback

    def start(self, delay=0):
        """
        Start the animation
        """
        if self.__inprogress is not None:
            raise RuntimeError('animation already playing')
        self.delay = int(float(delay) * config.fps)
        self.__inprogress = kaa.InProgress()
        self.current_frame_num = 0
        if not Animation.__active:
            # register to gobject
            Animation.__active = True
            gobject.timeout_add(1000 / config.fps, Animation._clutter_step)
        with _lock_lock:
            Animation.__animations.append(self)
        return self.__inprogress

    def stop(self):
        """
        Stop the animation
        """
        if self.__inprogress is None:
            return
        with _lock_lock:
            Animation.__animations.remove(self)
        kaa.MainThreadCallable(self.__inprogress.finish)(None)
        self.__inprogress = None
        self.callback = None

    def behave(self, behaviour, *args, **kwargs):
        """
        Add behaviour to the animation. If `behaviour` is a string, an
        object registered to that name will be created with the given
        arguments.
        """
        if isinstance(behaviour, (str, unicode)):
            behaviour = create_behaviour(behaviour, *args, **kwargs)
        self.behaviour.append(behaviour)
        return self

    def apply(self, widget):
        """
        Add a widget to the animation.
        """
        with _lock_lock:
            self.__refs.append(_weakref.ref(widget))

    def __inprogress__(self):
        """
        Return InProgress object finishing when the animation is done or
        None if the animation is not playing.
        """
        return self.__inprogress

    @property
    def is_playing(self):
        return self.__inprogress is not None

    @property
    def widgets(self):
        with _lock_lock:
            widgets = []
            for ref in self.__refs[:]:
                widget = ref()
                if widget is None:
                    self.__refs.remove(ref)
                else:
                    widgets.append(widget)
            return widgets

    def _clutter_animate(self, alpha_value):
        """
        Animate one step. This function is always called from the
        clutter mainloop. The lock is always set when this function is
        called.
        """
        widgets = self.widgets
        if not widgets:
            self.stop()
        for behaviour in self.behaviour:
            behaviour.apply(alpha_value, widgets)
        if self.callback:
            self.callback(alpha_value)

    @classmethod
    def _clutter_step(cls):
        """
        Class method to call all running animations. This function is
        called from the clutter thread using a gobject timer to ensure
        that delays in the main application to not disturb the
        animation.
        """
        if config.performance_debug:
            t1 = time.time()
            if config.performance_debug == 'fps' and Animation.__active is not True:
                log.info('fps timer %s', t1 - Animation.__active)
            Animation.__active = t1
        with _lock_lock:
            try:
                for a in cls.__animations[:]:
                    if a.delay:
                        a.delay -= 1
                        continue
                    a.current_frame_num += 1
                    a._clutter_animate(a.alpha_func(a.current_frame_num, a.n_frames))
                    if a.current_frame_num == a.n_frames:
                        a.stop()
                signals['candy-update'].emit()
            except Exception, e:
                log.exception('animation')
        if config.performance_debug:
            diff = time.time() - t1
            if diff > 0.02:
                log.warning('animations.step() took %2.3f secs' % diff)
        if cls.__animations:
            return True
        Animation.__active = False
        return False
