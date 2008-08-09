# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# behaviour.py - Behaviour Classes
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

__all__ = [ 'Behaviour', 'BehaviourOpacity', 'BehaviourScale', 'BehaviourColor',
            'create', 'register' ]

# kaa.candy imports
from core import Color
from alpha_func import MAX_ALPHA

_behaviour = {}

class Behaviour(object):
    """
    Behaviour base class
    """
    def __init__(self, start, end):
        self.start_value = start
        self.end_value = end
        if isinstance(start, (int, long, float)):
            self.diff = end - start
        if isinstance(start, (list, tuple)):
            self.diff = [ end[i] - start[i] for i in range(len(start)) ]

    def get_current(self, alpha_value):
        """
        Get current value between start and end based on alpha value.
        """
        if alpha_value == MAX_ALPHA:
            return self.end_value
        if alpha_value == 0:
            return self.start_value
        factor = float(alpha_value) / MAX_ALPHA
        if isinstance(self.start_value, (int, long, float)):
            return self.start_value + factor * self.diff
        return [ self.start_value[i] + factor * self.diff[i] \
                 for i in range(len(self.start_value)) ]

    def apply(self, alpha_value, widgets):
        """
        Update widgets based on alpha value
        @param alpha_value: alpha value between 0 and MAX_ALPHA
        @param widgets: widgets to modify
        """
        raise NotImplementedError

class BehaviourOpacity(Behaviour):
    """
    Behaviour to change the alpha value
    """
    def apply(self, alpha_value, widgets):
        """
        Update widgets based on alpha value
        @param alpha_value: alpha value between 0 and MAX_ALPHA
        @param widgets: widgets to modify
        """
        opacity = int(self.get_current(alpha_value))
        for widget in widgets:
            widget.opacity = opacity

class BehaviourScale(Behaviour):
    """
    Behaviour to scale widgets
    """
    def apply(self, alpha_value, widgets):
        """
        Update widgets based on alpha value
        @param alpha_value: alpha value between 0 and MAX_ALPHA
        @param widgets: widgets to modify
        """
        scale = self.get_current(alpha_value)
        for widget in widgets:
            widget.scale = scale

class BehaviourMove(Behaviour):
    """
    Behaviour to move widgets
    """
    def apply(self, alpha_value, widgets):
        """
        Update widgets based on alpha value
        @param alpha_value: alpha value between 0 and MAX_ALPHA
        @param widgets: widgets to modify
        """
        x, y = self.get_current(alpha_value)
        for widget in widgets:
            widget.x = int(x)
            widget.y = int(y)

class BehaviourColor(Behaviour):
    """
    Behaviour to change the color
    """
    def apply(self, alpha_value, widgets):
        """
        Update widgets based on alpha value
        @param alpha_value: alpha value between 0 and MAX_ALPHA
        @param widgets: widgets to modify
        """
        color = []
        for pos in range(4):
            start = self.start_value[pos]
            diff =  self.end_value[pos] - start
            alpha = float(alpha_value) / MAX_ALPHA
            color.append(start + int(diff * alpha))
        color = Color(*color)
        for widget in widgets:
            widget.color = color

# register behaviours
_behaviour['opacity'] = BehaviourOpacity
_behaviour['scale'] = BehaviourScale
_behaviour['move'] = BehaviourMove
_behaviour['color'] = BehaviourColor

def create(name, *args, **kwargs):
    return _behaviour.get(name)(*args, **kwargs)

def register(name, cls):
    _behaviour[name] = cls
