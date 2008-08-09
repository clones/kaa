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

__all__ = [ 'Animation' ]

# python imports
import time
import logging
import gobject

# kaa imports
import kaa

# kaa.candy imports
import config
from behaviour import create_alpha, create_behaviour

# get logging object
log = logging.getLogger('kaa.candy')

# signal to trigger redraw
signals = {
    'candy-update': kaa.Signal()
}

class Animation(object):
    """
    Basic animation class.
    """
    __animations = []
    __active = False
    running = None

    def __init__(self, secs, alpha_func='inc'):
        self.current_frame_num = 0
        self.n_frames = int(float(secs) * config.fps)
        if isinstance(alpha_func, str):
            alpha_func = create_alpha(alpha_func)
        self.alpha_func = alpha_func
        self.behaviour = []
        self.widgets = []

    def start(self):
        if self.running is not None:
            raise RuntimeError('animation already running')
        self.running = kaa.InProgress()
        self.current_frame_num = 0
        if not Animation.__active:
            # FIXME: maybe use clutter.Timeline here
            Animation.__active = True
            gobject.timeout_add(1000 / config.fps, Animation.__step)
        Animation.__animations.append(self)
        return self.running

    def stop(self):
        Animation.__animations.remove(self)
        self.running.finish(None)
        self.running = None

    def is_playing(self):
        return self.running is not None

    def behave(self, behaviour, *args, **kwargs):
        if isinstance(behaviour, str):
            behaviour = create_behaviour(behaviour, *args, **kwargs)
        self.behaviour.append(behaviour)
        return self

    def apply(self, widget):
        self.widgets.append(widget)

    def _candy_animate(self, alpha_value):
        for behaviour in self.behaviour:
            behaviour.apply(alpha_value, self.widgets)

    @classmethod
    def __step(cls):
        # TIME DEBUG
        # t1 = time.time()
        for a in cls.__animations[:]:
            a.current_frame_num += 1
            a._candy_animate(a.alpha_func(a.current_frame_num, a.n_frames))
            if a.current_frame_num == a.n_frames:
                a.stop()
        signals['candy-update'].emit()
        # TIME DEBUG
        # print 'animation took %2.3f' % (time.time() - t1)
        if cls.__animations:
            return True
        Animation.__active = False
        return False
