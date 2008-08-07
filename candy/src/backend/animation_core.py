# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - Animation Core
# -----------------------------------------------------------------------------
# $Id$
#
# THIS MODULE IS DEPRECATED AND DOES NOT WORK
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

__all__ = [ 'Animation', 'AnimationModifier' ]

# python imports
import logging

# kaa imports
import kaa

# clutter imports
import clutter

# kaa.candy imports
from .. import config, candyxml, threaded, Modifier

# get logging object
log = logging.getLogger('kaa.candy')

class XMLDict(dict):
    """
    XML parser dict helper class.
    """
    def update(self, **kwargs):
        super(XMLDict, self).update(**kwargs)
        return self


class Template(object):
    """
    Template to create an animation on demand. All XML parser will create such an
    object to parse everything during theme parsing.
    """
    def __init__(self, style, cls, kwargs):
        self.style = style
        self._cls = cls
        self._kwargs = kwargs

    def __call__(self, widget, context=None):
        """
        Create the animation bound to the given widget.
        """
        return self._cls(widget, context=context, **self._kwargs)

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the XML element for parameter and create a Template.
        """
        animation = candyxml.get_class(element.node, element.style)
        if not animation:
            return None
        return cls(element.style, animation, animation.candyxml_parse(element))


class Animation(kaa.InProgress):
    """
    Base animation class.
    """

    __template__ = Template
    candyxml_name = 'animation'

    def __init__(self, secs):
        super(Animation, self).__init__()
        fps = config.fps
        self.timeline = clutter.Timeline(int(float(secs) * fps), fps)
        self.timeline.set_loop(False)
        # FIXME: do not hardcode alpha function
        self.alpha = clutter.Alpha(self.timeline, clutter.ramp_inc_func)

    def _start(self, widgets, behaviour, effects):
        """
        Start the animation.
        """
        # store reference to the behaviour or the animation won't run
        self.behaviour = behaviour
        self.widgets = widgets

        # store reference to ourself
        for widget in widgets:
            for e in effects:
                # set behaviour for the effect. This may override
                # existing behaviour with the same effect, they
                # will be removed to avoid race conditions.
                running = widget._running_animations.get(e, None)
                if running is not None:
                    running.stop()
                widget._running_animations[e] = self
            # This creates a circular reference which will be resolved
            # on the destroy signal callback in widgets/core.py
        self.timeline.start()
        self.timeline.connect('completed', self._clutter_finish)

    def _clutter_finish(self, result=None):
        """
        Callback from any thread when the animation is finished.
        """
        # delete all references
        for widget in self.widgets:
            for key, value in widget._running_animations.items():
                if value == self:
                    del widget._running_animations[key]
        self.timeline.disconnect_by_func(self._clutter_finish)
        self.timeline = self.alpha = self.behaviour = self.widgets = None
        super(Animation, self).finish(result)

    def _clutter_stop(self):
        """
        Stop the animation
        """
        if self.timeline is None:
            # already done
            return
        self.timeline.stop()
        self._clutter_finish()

    @threaded()
    def stop(self):
        """
        Stop the animation
        """
        self._clutter_finish()

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return XMLDict(secs=float(element.secs))

    @classmethod
    def candyxml_register(cls):
        """
        Register animation to candyxml. This function can only be called
        once when the class is loaded.
        """
        candyxml.register(cls)

#     def __del__(self):
#         print '__del__', self

class AnimationModifier(Modifier):
    """
    Widget modifier to add additional animations.
    """
    candyxml_name = 'define-animation'

    def __init__(self, style, animations, modifier):
        self._style = style
        self._animations = animations
        self._modifier = modifier

    def modify(self, widget):
        """
        Modify the given widget.
        @param widget: widget to modify
        @returns: same widget
        """
        widget.set_animation(self._style, self)
        return widget

    def __call__(self, widget, context=None):
        """
        Create the animation bound to the given widget.
        """
        for modifier in self._modifier:
            widget = modifier.modify(widget)
        return [ a(widget, context) for a in self._animations ]

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the candyxml element for parameter and create the Modifier.
        """
        modifier = []
        animations = []
        for subelement in element:
            mod = Modifier.candyxml_create(subelement)
            if mod:
                modifier.append(mod)
            elif subelement.node == 'animation':
                a = subelement.xmlcreate()
                if a is None:
                    log.error('unknown animation %s', subelement.style)
                else:
                    animations.append(a)
            else:
                log.error('unknown element %s in define-animation', subelement.node)
        return cls(element.style, animations, modifier)

# register the modifier
AnimationModifier.candyxml_register()
