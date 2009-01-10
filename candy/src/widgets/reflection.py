# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# reflection.py - Reflection Widget
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

__all__ = [ 'Reflection', 'ReflectionModifier' ]

# python imports
import logging

# kaa imports
from kaa.utils import property

# kaa.candy imports
from .. import Modifier
from .. import backend
from container import Group

# get logging object
log = logging.getLogger('kaa.candy')


class Reflection(Group):
    """
    Widget containing a widget and its reflection actor.
    """
    def __init__(self, widget, opacity):
        """
        Create new group of widget and reflection.

        @param widget: source widget (will be added to the group)
        @param opacity: opacity of the reflection.
        """
        super(Reflection, self).__init__((widget.x, widget.y))
        self.context_sensitive = widget.context_sensitive
        self.source = widget
        self.x, self.y = self.source.x, self.source.y
        self.source.x = self.source.y = 0
        self.add(self.source)
        self._reflection_opacity = opacity
        self._reflection_obj = None
        self._dynamic_size = self.source._dynamic_size

    def _clutter_render(self):
        """
        Render the widget
        """
        super(Reflection, self)._clutter_render()
        if 'size' in self._sync_properties:
            self.source.width = self.width
            self.source.height = self.height
        if not self._reflection_obj:
            self._reflection_obj = backend.ReflectTexture(self.source._obj, 0)
            self._reflection_obj.show()
            self._reflection_obj.set_opacity(self._reflection_opacity)
            self._obj.add(self._reflection_obj)

    def _clutter_sync_layout(self):
        """
        Layout the widget
        """
        # Get the source's size and set the anchor_point. We MUST do
        # this before calling super's sync function to avoid
        # triggering a re-layout when setting the anchor_point.
        width, height = self.source._obj.get_size()
        self.anchor_point = width/2, height
        super(Reflection, self)._clutter_sync_layout()
        # get source's position to set the reflection
        x, y = self.source._obj.get_position()
        self._reflection_obj.set_property('reflection-height', height / 2)
        if self.subpixel_precision:
            # FIXME: this code does not respect subpixel_precision because it
            # uses the int values from the source
            self._reflection_obj.set_anchor_pointu(*self.source._obj.get_anchor_pointu())
            self._reflection_obj.set_positionu(x, y + height)
            self._reflection_obj.set_sizeu(width, height)
        else:
            self._reflection_obj.set_anchor_point(*self.source._obj.get_anchor_point())
            self._reflection_obj.set_position(int(x), int(y + height))
            self._reflection_obj.set_size(int(width), int(height))

    def _candy_context_prepare(self, context):
        """
        Check if the widget is capable of the given context based on its
        dependencies.
        @param context: context dict
        @returns: False if the widget can not handle the context or True
        """
        # This widget does only depend indirect on a context. The real widget
        # inside may depend on a context and the reflection depends on the
        # widget. So we just use the widget _candy_context_prepare function here.
        return self.source._candy_context_prepare(context)

    def _candy_context_sync(self, context):
        """
        Set a new context.

        @param context: context dict
        """
        # This widget does only depend indirect on a context. The real widget
        # inside may depend on a context and the reflection depends on the
        # widget. So we just use the widget _candy_context_sync function here.
        return self.source._candy_context_sync(context)

    @property
    def width(self):
        return self.source.width

    @width.setter
    def width(self, width):
        self.source.width = width
        self._dynamic_size = self.source._dynamic_size

    @property
    def height(self):
        return self.source.height

    @height.setter
    def height(self, height):
        self.source.height = height
        self._dynamic_size = self.source._dynamic_size

    @property
    def intrinsic_size(self):
        return self.source.intrinsic_size

class ReflectionModifier(Modifier):
    """
    Modifier to add a reflection.
    """

    candyxml_name = 'reflection'

    def __init__(self, opacity=50):
        """
        Create modifier

        @param opacity: opacity of the reflection
        """
        self._opacity = opacity

    def modify(self, widget):
        """
        Modify the given widget.

        @param widget: widget to modify
        @returns: Group widget with src and reflection textures
        """
        return Reflection(widget, self._opacity)

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the candyxml element and create the modifier. Any texture based
        widget can be used as base. Example::
          <image width='100' height='100'>
              <reflection opacity='50'/>
          </image>
        """
        return cls(opacity = int(element.opacity or 50))
