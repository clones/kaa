# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# widget.py - Core Widget and Template
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

__all__ = [ 'Widget' ]

# python imports
import logging
import _weakref
import re

# kaa imports
import kaa
import kaa.imlib2
from kaa.utils import property

# kaa.candy imports
from .. import candyxml, animation, Modifier, backend, thread_enter, thread_leave, Context

# get logging object
log = logging.getLogger('kaa.candy')

class _dict(dict):
    """
    XML parser dict helper class.
    """
    def update(self, **kwargs):
        super(_dict, self).update(**kwargs)
        return self


class Template(object):
    """
    Template to create a widget on demand. All XML parsers will create such an
    object to parse everything at once.
    """

    #: class is a template class
    __is_template__ = True

    def __init__(self, cls, **kwargs):
        """
        Create a template for the given class

        @param cls: widget class
        @param kwargs: keyword arguments for cls.__init__
        """
        self._cls = cls
        self._modifier = kwargs.pop('modifier', [])
        self._kwargs = kwargs
        self.userdata = {}

    def __call__(self, context=None):
        """
        Create the widget with the given context and override some
        constructor arguments.

        @param context: context to create the widget in
        @returns: widget object
        """
        if context is not None:
            context = Context(context)
        if self._cls.context_sensitive:
            self._kwargs['context'] = context
        widget = self._cls(**self._kwargs)
        for modifier in self._modifier:
            widget = modifier.modify(widget)
        return widget

    @classmethod
    def candyxml_get_class(cls, element):
        """
        Get the class for the candyxml element. This function may be overwritten
        by inheriting classes and should not be called from outside such a class.
        """
        return candyxml.get_class(element.node, element.style)

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the candyxml element for parameter and create a Template.

        @param element: kaa.candy.candyxml.Element with widget information
        @returns: Template object
        """
        modifier = []
        for subelement in element.get_children():
            mod = Modifier.candyxml_create(subelement)
            if mod:
                modifier.append(mod)
                element.remove(subelement)
        widget = cls.candyxml_get_class(element)
        if widget is None:
            log.error('undefined widget %s:%s', element.node, element.style)
        kwargs = widget.candyxml_parse(element)
        if modifier:
            kwargs['modifier'] = modifier
        template = cls(widget, **kwargs)
        return template


class Widget(object):
    """
    Basic widget. All widgets from the backend must inherit from it.

    @cvar context_sensitive: class variable for inherting class if the class
        depends on the context.
    """

    #: set if the object reacts on context
    context_sensitive = False

    #: template for object creation
    __template__ = Template

    # sync indications
    _sync_rendering = True
    _sync_layout = True

    # properties
    __parent = None
    __anchor = None
    __x = 0
    __y = 0
    __width = 0
    __height = 0
    __xalign = None
    __yalign = None
    __xpadding = 0
    __ypadding = 0
    __scale = None
    __depth = 0
    __opacity = 255
    __rotation = 0

    # misc
    name = None
    _obj = None

    ALIGN_LEFT = 'left'
    ALIGN_RIGHT = 'right'
    ALIGN_TOP = 'top'
    ALIGN_BOTTOM = 'bottom'
    ALIGN_CENTER = 'center'

    __re_eval = re.compile('\.[a-zA-Z][a-zA-Z0-9_]*')

    def __init__(self, pos=None, size=None, context=None):
        """
        Basic widget constructor.

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param context: the context the widget is created in
        """
        if size is not None:
            self.__width, self.__height = size
        if pos is not None:
            self.__x, self.__y = pos
        self._sync_properties = {}
        self.__depends = {}
        self.__context = context or {}
        self.userdata = {}

    def add_dependency(self, var):
        """
        Evaluate the context for the given variable and depend on the result

        @param var: variable name to eval
        """
        self.__depends[var] = repr(self.__context.get(var))

    def animate(self, secs, alpha='inc', unparent=False):
        """
        Animate the object with the given animation. This returns an
        Animation object to add the behaviours. The animation is already
        started when this function returns.

        @param secs: number of seconds to run
        @param alpha: alpha function for this animation
        @param unparent: if set to True the widget will be unparented after the
            animation is finished.
        @note: in future version the alpha parameter will move to the behaviours
        """
        a = animation.Animation(secs, alpha)
        a.apply(self)
        a.start()
        if unparent:
            kaa.inprogress(a).connect(setattr, self, 'parent', None).set_ignore_caller_args()
        return a

    def raise_top(self):
        """
        Raise widget to the top of its group.
        """
        if self.parent:
            self.parent._candy_child_restack(self, 'top')

    def lower_bottom(self):
        """
        Lower widget to the bottom of its group.
        """
        if self.parent:
            self.parent._candy_child_restack(self, 'bottom')

    def __calculate_size(self):
        """
        Calculate width and height based on parent
        """
        # FIXME: this must be updated once the dependencies change. When width
        # or height is none a special variable sync_with_parent must be set and
        # the parent must reset __width and __height to None once it's inner
        # size values change. This must also trigger the resize property. This
        # values must also be updated when __x or __y of the widget change.
        # This code should also be used when width and height are based on
        # percentage of the parent width and height.
        if self.__width == None:
            # get width based on parent and x
            self.__width = self.parent.inner_width - self.x
        if self.__height == None:
            # get height based on parent and x
            # FIXME: this must be updated once the dependencies change
            self.__height = self.parent.inner_height - self.y

    # rendering sync

    def _queue_rendering(self):
        """
        Queue rendering on the next sync.
        """
        self._sync_rendering = True
        parent = self.parent
        if parent and not parent._sync_rendering:
            parent._queue_rendering()

    def _queue_sync_layout(self):
        """
        Queue re-layout to be called on the next sync.
        """
        self._sync_layout = True
        parent = self.parent
        if parent and not parent._sync_rendering and not parent._sync_layout:
            parent._queue_sync_layout()

    def _queue_sync_properties(self, *properties):
        """
        Queue clutter properties to be set on the next sync.
        """
        for prop in properties:
            self._sync_properties[prop] = True
        parent = self.parent
        if parent and not parent._sync_properties:
            parent._queue_sync_properties('children')

    def _candy_context_prepare(self, context):
        """
        Check if the widget is capable of the given context based on its
        dependencies. This function is not thread-safe and should only
        modify children not connected to any parent.

        @param context: context dict
        @returns: False if the widget can not handle the context or True
        """
        if self.__depends:
            try:
                for var, value in self.__depends.items():
                    if value != repr(context.get(var)):
                        return False
            except AttributeError:
                return False
        return True

    def _candy_context_sync(self, context):
        """
        Set a new context.

        @param context: dict of context key,value pairs
        """
        self.__context = context

    def _candy_prepare(self):
        """
        Prepare sync. This function may be called from the mainloop.
        """
        if self.__width == None or self.__height == None:
            self.__calculate_size()

    def prepare(self, parent=None):
        """
        Prepare sync, set parent while calling the prepare function
        """
        if parent:
            self.__parent = _weakref.ref(parent)
        self._candy_prepare()
        if parent:
            self.__parent = None

    # clutter rendering

    def _clutter_render(self):
        """
        Render the widget
        """
        raise NotImplemented

    def _clutter_sync_layout(self):
        """
        Layout the widget
        """
        self._sync_layout = False
        x, y = self.__x, self.__y
        anchor_x = anchor_y = 0
        if self.__xalign:
            if self.__xalign == Widget.ALIGN_CENTER:
                x += (self.__width - self._obj.get_width()) / 2
                anchor_x = self._obj.get_width() / 2
            elif self.__xalign == Widget.ALIGN_RIGHT:
                x += self.__width - self._obj.get_width() - self.__xpadding
                anchor_x = self._obj.get_width()
            else:
                x += self.__xpadding
        else:
            x += self.__xpadding
        if self.__yalign:
            if self.__yalign == Widget.ALIGN_CENTER:
                y += (self.__height - self._obj.get_height()) / 2
                anchor_y = self._obj.get_height() / 2
            elif self.__yalign == Widget.ALIGN_BOTTOM:
                y += self.__height - self._obj.get_height() - self.__ypadding
                anchor_y = self._obj.get_height()
            else:
                y += self.__ypadding
        else:
            y += self.__ypadding
        if self.__anchor:
            anchor_x, anchor_y = self.__anchor
        if anchor_x or anchor_y:
            self._obj.set_anchor_point(anchor_x, anchor_y)
            x += anchor_x
            y += anchor_y
        self._obj.set_position(x, y)

    def _clutter_sync_properties(self):
        """
        Set some simple properties of the clutter.Actor
        """
        if 'parent' in self._sync_properties:
            clutter_parent = self._sync_properties.pop('parent')
            if self._obj.get_parent():
                self._obj.get_parent().remove(self._obj)
            if not clutter_parent:
                # no need to do more
                return False
            clutter_parent.add(self._obj)
        if 'size' in self._sync_properties:
            if self.__rotation:
                self._sync_properties['rotation'] = True
        if 'scale' in self._sync_properties:
            self._obj.set_scale(*self.__scale)
        if 'depth' in self._sync_properties:
            self._obj.set_depth(self.__depth)
        if 'opacity' in self._sync_properties:
            self._obj.set_opacity(self.__opacity)
        if 'rotation' in self._sync_properties:
            # basic rotation, inherit from this class to not rotate
            # based on anchor_point or align
            self._obj.set_rotation(backend.Z_AXIS, self.__rotation, 0, 0, 0)
        return True

    # properties

    @property
    def x(self):
        return self.__x

    @x.setter
    def x(self, x):
        if self.__x == x:
            return
        self.__x = x
        self._queue_sync_layout()

    @property
    def y(self):
        return self.__y

    @y.setter
    def y(self, y):
        if self.__y == y:
            return
        self.__y = y
        self._queue_sync_layout()

    @property
    def width(self):
        if self.__width == None:
            self.__calculate_size()
        return self.__width

    @width.setter
    def width(self, width):
        if self.__width == width:
            return
        if self._obj is not None:
            self._queue_sync_properties('size')
        self.__width = width
        self._queue_rendering()
        self._queue_sync_layout()

    @property
    def inner_width(self):
        if self.__width == None:
            self.__calculate_size()
        return self.__width - 2 * self.__xpadding

    @property
    def height(self):
        if self.__height == None:
            self.__calculate_size()
        return self.__height

    @height.setter
    def height(self, height):
        if self.__height == height:
            return
        if self._obj is not None:
            self._queue_sync_properties('size')
        self.__height = height
        self._queue_rendering()
        self._queue_sync_layout()

    @property
    def inner_height(self):
        if self.__height == None:
            self.__calculate_size()
        return self.__height - 2 * self.__ypadding

    @property
    def geometry(self):
        if self.__width == None or self.__height == None:
            self.__calculate_size()
        return self.__x, self.__y, self.__width, self.__height

    @property
    def anchor_point(self):
        return self.__anchor or (0, 0)

    @anchor_point.setter
    def anchor_point(self, (x, y)):
        self.__anchor = x, y
        self._queue_sync_layout()

    @property
    def xalign(self):
        return self.__xalign or Widget.ALIGN_LEFT

    @xalign.setter
    def xalign(self, align):
        self.__xalign = align
        self._queue_sync_layout()

    @property
    def yalign(self):
        return self.__yalign or Widget.ALIGN_TOP

    @yalign.setter
    def yalign(self, align):
        self.__yalign = align
        self._queue_sync_layout()

    @property
    def xpadding(self):
        return self.__xpadding

    @xpadding.setter
    def xpadding(self, padding):
        self.__xpadding = padding
        self._queue_rendering()

    @property
    def ypadding(self):
        return self.__ypadding

    @ypadding.setter
    def ypadding(self, padding):
        self.__ypadding = padding
        self._queue_rendering()

    @property
    def scale(self):
        return self.__scale or (1, 1)

    @scale.setter
    def scale(self, (x, y)):
        self.__scale = x, y
        self._queue_sync_properties('scale')

    @property
    def depth(self):
        return self.__depth

    @depth.setter
    def depth(self, depth):
        self.__depth = depth
        self._queue_sync_properties('depth')

    @property
    def opacity(self):
        return self.__opacity

    @opacity.setter
    def opacity(self, opacity):
        self.__opacity = opacity
        self._queue_sync_properties('opacity')

    @property
    def rotation(self):
        return self.__rotation

    @rotation.setter
    def rotation(self, rotation):
        self.__rotation = rotation
        self._queue_sync_properties('rotation')

    @property
    def parent(self):
        if self.__parent is None:
            return None
        return self.__parent()

    @parent.setter
    def parent(self, parent):
        if self.__parent is not None:
            curent = self.__parent()
            if curent is not None:
                curent._candy_child_remove(self)
        self.__parent = None
        if parent:
            self.__parent = _weakref.ref(parent)
            parent._candy_child_add(self)

    @property
    def context(self):
        return self.__context

    @context.setter
    def context(self, context):
        context = Context(context)
        self._candy_context_prepare(context)
        thread_enter()
        try:
            self._candy_context_sync(context)
        finally:
            thread_leave()

    # candyxml stuff

    @classmethod
    def create_template(cls, **kwargs):
        """
        Create a template for this class.

        @param kwargs: keyword arguments based on the class __init__ function
        """
        return cls.__template__(cls, **kwargs)

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the candyxml element for parameter to create the widget. This function
        must be overwitten by a subclass for the correct parsing. This class
        only parses pos and size::
          <widget x='10' y='20' width='100' height='50'/>
        """
        return _dict(pos=element.pos, size=(element.width, element.height))

    @classmethod
    def candyxml_register(cls, style=None):
        """
        Register class to candyxml. This function can only be called
        once when the class is loaded.
        """
        candyxml.register(cls, style)

#     def __del__(self):
#         print '__del__', self
