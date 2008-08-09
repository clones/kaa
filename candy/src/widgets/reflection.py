# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# reflection.py - Reflection Widget
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

__all__ = [ 'Reflection', 'ReflectionModifier' ]

# python imports
import logging
import gtk
import cairo

# kaa.candy imports
from .. import Modifier
from .. import backend
import core

# get logging object
log = logging.getLogger('kaa.candy')


class Reflection(core.Group):
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
        self.source.parent = self
        self._reflection_opacity = opacity

    def _candy_render(self):
        """
        Render the widget
        """
        if 'size' in self._sync_properties:
            log.error('FIXME: kaa.candy.Reflection does not support resize')
            return
        self._obj = backend.Group()
        self.source._candy_sync()
        # FIXME: do not access _obj of a different widget
        actor = self.source._obj
        w, h = actor.get_size()
        self.anchor_point = w/2, h
        actor.set_position(0,0)
        reflection = backend.ReflectTexture(actor, h/2)
        # reflection = backend.CairoReflectTexture(actor)
        reflection.set_size(w, h)
        reflection.set_position(0, h)
        reflection.show()
        self._obj.add(reflection)
        reflection.set_opacity(self._reflection_opacity)

    def try_context(self, context):
        """
        Check if the widget is capable of the given context based on its
        dependencies. If it is possible set the context.
        @param context: context dict
        @returns: False if the widget can not handle the context or True
        """
        # This widget does only depend indirect on a context. The real widget
        # inside may depend on a context and the reflection depends on the
        # widget. So we just use the widget try_context function here.
        return self.source.try_context(context)


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

# register widget to the core
ReflectionModifier.candyxml_register()
