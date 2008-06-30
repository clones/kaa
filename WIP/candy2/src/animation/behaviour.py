# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# behaviour.py - Additional Behaviour Classes
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008 Dirk Meyer, Jason Tackaberry
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

__all__ = [ 'BehaviourColor' ]

# clutter imports
import clutter

# kaa.candy imports
from ..core import Color

class BehaviourColor(clutter.Behaviour):
    """
    Behaviour to change the color of an actor.
    """
    __gtype_name__ = 'BehaviourColor'

    def __init__ (self, alpha, start_color, end_color):
        clutter.Behaviour.__init__(self)
        self.set_alpha(alpha)
        self._start = start_color
        self._end = end_color

    def do_alpha_notify(self, alpha_value):
        color = []
        for pos in range(4):
            start = self._start[pos]
            diff =  self._end[pos] - start
            alpha = float(alpha_value) / clutter.MAX_ALPHA
            color.append(start + int(diff * alpha))
        for actor in self.get_actors():
            actor.set_color(Color(*color))
