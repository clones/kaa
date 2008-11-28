# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - Helper classes and decorator
# -----------------------------------------------------------------------------
# $Id: core.py 3516 2008-08-27 20:12:08Z dmeyer $
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

# python imports
import logging

# kaa imports
import kaa

# kaa.candy imports
import core

# get logging object
log = logging.getLogger('kaa.candy')

class Eventhandler(core.Modifier):
    """
    """

    #: candyxml name
    candyxml_name = 'eventhandler'

    def __init__(self, event):
        self.event = event
        self.condition = None
        self.animations = []
        self.process_children = False

    def modify(self, widget):
        """
        Apply to the given widget.

        @param widget: a kaa.candy.Widget
        """
        if not self.event in widget.eventhandler:
            widget.eventhandler[self.event] = []
        widget.eventhandler[self.event].append(self)
        return widget

    def __call__(self, widget, context):
        if self.condition:
            if not eval(self.condition, context):
                return kaa.InProgressAll()
        async = []
        for animation in self.animations:
            if animation.behaviour == 'move':
                x1 = x2 = widget.x
                if animation.x1 is not None:
                    x1 = animation.get_scaled('x1', 0, int)
                if animation.x2 is not None:
                    x2 = animation.get_scaled('x2', 0, int)
                y1 = y2 = widget.y
                if animation.y1 is not None:
                    y1 = animation.get_scaled('y1', 1, int)
                if animation.y2 is not None:
                    y2 = animation.get_scaled('y2', 1, int)
                start = x1, y1
                end = x2, y2
                widget.x = x1
                widget.y = y1
            elif animation.behaviour == 'opacity':
                start = end = widget.opacity
                if animation.start is not None:
                    start = int(animation.start)
                if animation.end is not None:
                    end = int(animation.end)
                widget.opacity = start
            else:
                log.error('unsupported behaviour %s', animation.behaviour)
                continue
            a = widget.animate(float(animation.secs or 1),
                  delay=float(animation.delay or 0))
            a.behave(animation.behaviour, start, end)
            async.append(kaa.inprogress(a))
        if self.process_children:
            for child in widget.children:
                eventhandler = child.eventhandler.get(self.event)
                if eventhandler is not None:
                    async.extend([ x(child, context) for x in eventhandler])
        return kaa.InProgressAll(*async)

    @classmethod
    def candyxml_create(cls, element):
        """
        """
        eventhandler = cls(element.event)
        for child in element:
            if child.node == 'animate':
                eventhandler.animations.append(child)
            if child.node == 'process-children':
                eventhandler.process_children = True
        eventhandler.condition = element.condition
        return eventhandler
