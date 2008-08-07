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

__all__ = [ 'Behaviour', 'BehaviourOpacity', 'BehaviourScale', 'BehaviourColor' ]

# kaa.candy imports
from ..core import Color
from alpha import MAX_ALPHA

class Behaviour(object):
    """
    Behaviour base class
    """
    def __init__(self, start, end):
        self.start_value = start
        self.end_value = end
        if isinstance(start, (int, long)):
            self.diff = end - start
        if isinstance(start, (list, tuple)):
            self.diff = [ end[1] - start[i] for i in range(len(start)) ]

    def set_alpha(self, alpha_value, widgets):
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
    def set_alpha(self, alpha_value, widgets):
        """
        Update widgets based on alpha value
        @param alpha_value: alpha value between 0 and MAX_ALPHA
        @param widgets: widgets to modify
        """
        opacity = alpha_value * self.diff / MAX_ALPHA + self.start_value;
        for widget in widgets:
            widget.opacity = opacity

class BehaviourScale(Behaviour):
    """
    Behaviour to change the alpha value
    """
    def set_alpha(self, alpha_value, widgets):
        """
        Update widgets based on alpha value
        @param alpha_value: alpha value between 0 and MAX_ALPHA
        @param widgets: widgets to modify
        """
        if alpha_value == MAX_ALPHA:
            scale_x = self.end_value[0]
            scale_y = self.end_value[1]
        else:
            scale_x = self.start_value[0]
            scale_y = self.start_value[1]
            if alpha_value > 0:
                factor = float(alpha_value) / MAX_ALPHA
                scale_x += factor * self.diff[0]
                scale_y += factor * self.diff[1]
        for widget in widgets:
            widget.scale = scale_x, scale_y

class BehaviourColor(Behaviour):
    """
    Behaviour to change the color
    """
    def set_alpha(self, alpha_value, widgets):
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
