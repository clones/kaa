# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - Animation Core
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008 Dirk Meyer, Jason Tackaberry
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

__all__ = [ 'Animation', 'thread_enter', 'thread_leave', 'thread_locked' ]

"""
Animation submodule

@todo: add function to loop an animation
@todo: add pause function
"""

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

    def __init__(self, secs, alpha_func='inc'):
        """
        Create an animation

        @param secs: runtime of the animation
        @param alpha_func: alpha_func to apply to the behaviours
        """
        self.current_frame_num = 0
        self.n_frames = int(float(secs) * config.fps)
        if isinstance(alpha_func, str):
            alpha_func = create_alpha(alpha_func)
        self.alpha_func = alpha_func
        self.behaviour = []
        self.__refs = []

    def start(self):
        """
        Start the animation
        """
        if self.__inprogress is not None:
            raise RuntimeError('animation already playing')
        self.__inprogress = kaa.InProgress()
        self.current_frame_num = 0
        if not Animation.__active:
            # register to gobject
            Animation.__active = True
            gobject.timeout_add(1000 / config.fps, Animation.__step)
        Animation.__animations.append(self)
        return self.__inprogress

    def stop(self):
        """
        Stop the animation
        """
        if self.__inprogress is None:
            return
        Animation.__animations.remove(self)
        self.__inprogress.finish(None)
        self.__inprogress = None

    def behave(self, behaviour, *args, **kwargs):
        """
        Add behaviour to the animation

        @param behaviour: Behaviour object or string. If behaviour is a
            string, an object registered to that name will be created
            with the given arguments.
        """
        if isinstance(behaviour, str):
            behaviour = create_behaviour(behaviour, *args, **kwargs)
        self.behaviour.append(behaviour)
        return self

    def apply(self, widget):
        """
        Add a widget to the animation
        """
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
        widgets = []
        for ref in self.__refs[:]:
            widget = ref()
            if widget is None:
                self.__refs.remove(ref)
            else:
                widgets.append(widget)
        return widgets

    def _candy_animate(self, alpha_value):
        """
        Animate one step
        """
        widgets = self.widgets
        if not self.__refs:
            self.stop()
        for behaviour in self.behaviour:
            behaviour.apply(alpha_value, widgets)

    @classmethod
    def __step(cls):
        """
        Class method to call all running animations
        """
        _lock_lock.acquire()
        if config.performance_debug:
            t1 = time.time()
        try:
            for a in cls.__animations[:]:
                a.current_frame_num += 1
                a._candy_animate(a.alpha_func(a.current_frame_num, a.n_frames))
                if a.current_frame_num == a.n_frames:
                    a.stop()
                signals['candy-update'].emit()
            if config.performance_debug:
                diff = time.time() - t1
                if diff > 0.05:
                    log.warning('animations.step() took %2.3f secs' % diff)
        except Exception, e:
            log.exception('animation')
        _lock_lock.release()
        if cls.__animations:
            return True
        Animation.__active = False
        return False
