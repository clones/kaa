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
import logging
import gobject

# kaa imports
import kaa

# kaa.candy imports
from .. import config

# get logging object
log = logging.getLogger('kaa.candy')

# signal to trigger redraw
candy_update = kaa.Signal()

class Animation(object):
    """
    Basic animation class.
    """
    __animations = []
    __active = False
    running = None

    def __init__(self, secs, alpha):
        self.current_frame_num = 0
        self.n_frames = int(float(secs) * config.fps)
        self.alpha_func = alpha
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

    def stop(self):
        Animation.__animations.remove(self)
        self.running.finish(None)
        self.running = None

    def is_playing(self):
        return self.running is not None

    def apply(self, widget):
        # FIXME: add behaviour objects
        self.widgets.append(widget)

    def _candy_animate(self):
        # FIXME: add default with behaviour objects
        raise NotImplementedError

    @classmethod
    def __step(cls):
        for a in cls.__animations[:]:
            a.current_frame_num += 1
            a._candy_animate(a.alpha_func(a.current_frame_num, a.n_frames))
            if a.current_frame_num == a.n_frames:
                a.stop()
        candy_update.emit()
        if cls.__animations:
            return True
        Animation.__active = False
        return False
