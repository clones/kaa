# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# behaviour.py - Behaviour Classes
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008-2009 Dirk Meyer, Jason Tackaberry
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
            'MAX_ALPHA', 'create_behaviour', 'register_behaviour',
            'create_alpha', 'register_alpha', 'BehaviourXRotation',
            'BehaviourYRotation', 'BehaviourZRotation']

import sys

# kaa.candy imports
from core import Color

MAX_ALPHA = sys.maxint

_behaviour = {}
_alpha = {}

class Behaviour(object):
    """
    Behaviour base class. If target is not None, the widgets MUST be a
    Container and the behaviour will be applied to the child with the
    given name of that container. There will be no checks if this
    child exists and the behaviour will rause an exception if it does
    not.
    """
    def __init__(self, start, end, target=None):
        self.start_value = start
        self.end_value = end
        self.target = target
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
        if self.target:
            widgets = [ w.get_widget(self.target) for w in widgets ]
        self._apply(alpha_value, widgets)


class BehaviourOpacity(Behaviour):
    """
    Behaviour to change the alpha value
    """
    def _apply(self, alpha_value, widgets):
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
    def _apply(self, alpha_value, widgets):
        """
        Update widgets based on alpha value
        @param alpha_value: alpha value between 0 and MAX_ALPHA
        @param widgets: widgets to modify
        """
        scale = self.get_current(alpha_value)
        for widget in widgets:
            widget.scale = scale


class BehaviourXRotation(Behaviour):
    """
    Behaviour to change the x rotation value
    """
    def _apply(self, x_value, widgets):
        """
        Update widgets based on x rotation value
        @param x_value: x value between 0 and 365
        @param widgets: widgets to modify
        """
        rotation = int(self.get_current(x_value))
        for widget in widgets:
            widget.xrotation = rotation


class BehaviourYRotation(Behaviour):
    """
    Behaviour to change the y rotation value
    """
    def _apply(self, y_value, widgets):
        """
        Update widgets based on alpha value
        @param y rotation: y_value value between 0 and 360
        @param widgets: widgets to modify
        """
        rotation = int(self.get_current(y_value))
        for widget in widgets:
            widget.yrotation = rotation


class BehaviourZRotation(Behaviour):
    """
    Behaviour to change the z rotation value
    """
    def _apply(self, alpha_value, widgets):
        """
        Update widgets based on  z rotation value
        @param z rotation: z rotation value between 0 and 360
        @param widgets: widgets to modify
        """
        rotation = int(self.get_current(z_value))
        for widget in widgets:
            widget.zrotation = rotation


class BehaviourMove(Behaviour):
    """
    Behaviour to move widgets
    """
    def _apply(self, alpha_value, widgets):
        """
        Update widgets based on alpha value
        @param alpha_value: alpha value between 0 and MAX_ALPHA
        @param widgets: widgets to modify
        """
        x, y = self.get_current(alpha_value)
        for widget in widgets:
            widget.x = x
            widget.y = y


class BehaviourColor(Behaviour):
    """
    Behaviour to change the color
    """
    def __init__(self, start, end, attribute='color', target=None):
        super(BehaviourColor, self).__init__(start, end, target)
        self.attribute = attribute

    def _apply(self, alpha_value, widgets):
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
            setattr(widget, self.attribute, color)


# register behaviours
_behaviour['opacity'] = BehaviourOpacity
_behaviour['scale'] = BehaviourScale
_behaviour['move'] = BehaviourMove
_behaviour['color'] = BehaviourColor
_behaviour['xrotation'] = BehaviourXRotation
_behaviour['yrotation'] = BehaviourYRotation
_behaviour['zrotation'] = BehaviourZRotation

def create_behaviour(name, *args, **kwargs):
    return _behaviour.get(name)(*args, **kwargs)

def register_behaviour(name, cls):
    _behaviour[name] = cls

def alpha_inc_func(current_frame_num, n_frames):
    return (current_frame_num * MAX_ALPHA) / n_frames;

# register alpha functions
_alpha['inc'] = alpha_inc_func

def create_alpha(name, *args, **kwargs):
    return _alpha.get(name)

def register_alpha(name, func):
    _alpha[name] = func
