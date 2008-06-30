# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# simple.py - Simple Animations for widget.animate
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

__all__ = [ 'Scale', 'Opacity', 'Move', 'Color' ]

# clutter imports
import clutter

# kaa.candy imports
from core import Animation
from behaviour import BehaviourColor


class Scale(Animation):
    """
    Zoom-out the given object.
    """
    candyxml_style = 'scale'

    def __init__(self, obj, secs, x_factor, y_factor, context=None):
        super(Scale, self).__init__(secs)
        s = obj.get_scale()
        scale = clutter.BehaviourScale(s[0], s[1], x_factor, y_factor, self.alpha)
        scale.apply(obj)
        # give references to start function
        self._start([ obj ], scale, [ 'scale' ])

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return super(Scale, cls).candyxml_parse(element).update(
            x_factor=float(element.x_factor), y_factor=float(element.y_factor))


class Opacity(Animation):
    """
    Fade in or out the given object.
    """
    candyxml_style = 'opacity'

    def __init__(self, obj, secs, stop, context=None):
        try:
            super(Opacity, self).__init__(secs)
        except Exception, e:
            print e
        opacity = clutter.BehaviourOpacity(obj.get_opacity(), stop, self.alpha)
        opacity.apply(obj)
        # give references to start function
        self._start([ obj ], opacity, [ 'opacity' ])

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return super(Opacity, cls).candyxml_parse(element).update(
            stop=int(element.stop))


class Move(Animation):
    """
    Move the given object.
    """
    candyxml_style = 'move'

    def __init__(self, obj, secs, x=None, y=None, context=None):
        super(Move, self).__init__(secs)
        x0, y0 = obj.get_position()
        if x is None:
            x = x0
        if y is None:
            y = y0
        path = clutter.BehaviourPath(self.alpha, ((x0, y0), (x, y)))
        path.apply(obj)
        # give references to start function
        self._start([ obj ], path, [ 'move' ])

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return super(Move, cls).candyxml_parse(element).update(
            x=int(element.x), y=int(element.y))


class Color(Animation):
    """
    Color change animation.
    """
    candyxml_style = 'color'

    def __init__(self, obj, secs, color, context=None):
        super(Color, self).__init__(secs)
        color = BehaviourColor(self.alpha, obj.get_color(), color)
        color.apply(obj)
        # give references to start function
        self._start([ obj ], color, [ 'color' ])

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return super(Move, cls).candyxml_parse(element).update(
            x=int(element.x), y=int(element.y))


# register the animations to candyxml
Scale.candyxml_register()
Opacity.candyxml_register()
Move.candyxml_register()
Color.candyxml_register()
