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
        """
        modifier = []
        for subelement in element.get_children():
            mod = Modifier.candyxml_create(subelement)
            if mod is not None:
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

    class __metaclass__(type):
        def __new__(meta, name, bases, attrs):
            cls = type.__new__(meta, name, bases, attrs)
            if 'candyxml_name' in attrs.keys() or 'candyxml_style' in attrs.keys():
                candyxml.register(cls)
            return cls

    #: set if the object reacts on context
    context_sensitive = False

    #: template for object creation
    __template__ = Template

    # passive widgets with dynamic size depend on the size of the
    # other widgets in a container
    passive = False

    # subpixel precision for geometry values
    subpixel_precision = False

    # sync indications
    _sync_rendering = True
    _sync_layout = True

    # properties
    _candy__parent = None
    __anchor = None
    __x = 0.0
    __y = 0.0
    __width = None
    __height = None
    __xalign = None
    __yalign = None
    __xpadding = 0
    __ypadding = 0
    __scale = None
    __depth = 0
    __opacity = 255
    __rotation = 0
    # real size of the object, should be set by the widget
    _intrinsic_size = None

    # dynamic size calculation (percent)
    __dynamic_width = None
    __dynamic_height = None
    __dynamic_parent_size = None

    # misc
    name = None
    _obj = None

    ALIGN_LEFT = 'left'
    ALIGN_RIGHT = 'right'
    ALIGN_TOP = 'top'
    ALIGN_BOTTOM = 'bottom'
    ALIGN_CENTER = 'center'
    ALIGN_SHRINK = 'shrink'

    __re_eval = re.compile('\.[a-zA-Z][a-zA-Z0-9_]*')

    def __init__(self, pos=None, size=None, context=None):
        """
        Basic widget constructor. If size is None, the width and
        height will be treaded as None, None. If one value is None it
        will be calculated based on x or y to fit in the parent. If it
        is a string with percent values it will be the perecent of the
        parent's width and height. Fot passive widgets it will be the
        width or height of the non-passive content.
        """
        if size is not None:
            self.__width, self.__height = size
            if isinstance(self.__width, str):
                # use perecent values provided by the string
                self.__dynamic_width = int(self.__width[:-1])
                self.__width = None
            elif self.__width is None:
                # None means fit (-1)
                self.__dynamic_width = -1
            if isinstance(self.__height, str):
                # use perecent values provided by the string
                self.__dynamic_height = int(self.__height[:-1])
                self.__height = None
            elif self.__height is None:
                # None means fit (-1)
                self.__dynamic_height = 100
        else:
            # fit both width and height
            self.__dynamic_width = self.__dynamic_height = -1
        # store if this widget depends on the parent size
        self._dynamic_size = self.__dynamic_width or self.__dynamic_height
        if pos is not None:
            self.__x, self.__y = pos
        self._sync_properties = {}
        self.__depends = {}
        self.__context = context or {}
        self.eventhandler = {}
        self.userdata = {}

    def add_dependency(self, var):
        """
        Evaluate the context for the given variable and depend on the result

        @param var: variable name to eval
        """
        self.__depends[var] = repr(self.__context.get(var))

    def animate(self, secs, alpha='inc', delay=0, unparent=False):
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
        a.start(delay)
        if unparent:
            kaa.inprogress(a).connect(self.unparent).ignore_caller_args = True
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

    def unparent(self):
        """
        Remove the widget from its parent.
        """
        if self.parent:
            self.parent.remove(self)

    def __calculate_size(self):
        """
        Calculate width and height based on parent
        """
        if self.passive and self.__dynamic_parent_size:
            # dynamic size for passive children
            if self.__width == None:
                # get width based on parent content
                if self.__dynamic_width == -1:
                    # handle None in the passive case
                    self.__width = self.__dynamic_parent_size[0]
                else:
                    self.__width = self.__dynamic_parent_size[0] * self.__dynamic_width / 100
            if self.__height == None:
                # get height based on parent content
                if self.__dynamic_height == -1:
                    # handle None in the passive case
                    self.__height = self.__dynamic_parent_size[1]
                else:
                    self.__height = self.__dynamic_parent_size[1] * self.__dynamic_height / 100
            return
        # non passive children
        if self.__width == None:
            if self.__dynamic_width == -1:
                # fit into the parent
                self.__width = self.parent.inner_width - self.x
            else:
                # use percentage of parent
                self.__width = self.parent.inner_width * self.__dynamic_width / 100
        if self.__height == None:
            if self.__dynamic_height == -1:
                # fit into the parent
                self.__height = self.parent.inner_height - self.y
            else:
                # use percentage of parent
                self.__height = self.parent.inner_height * self.__dynamic_height / 100

    def _candy_calculate_dynamic_size(self, size=None):
        """
        Adjust dynamic change to parent size changes. This function
        returns True if the size changed. If size is given, this will
        be used as parent size (needed for passive widgets).
        """
        current = self.__width, self.__height
        if self.__dynamic_width is not None:
            self.__width = None
        if self.__dynamic_height is not None:
            self.__height = None
        self.__dynamic_parent_size = size
        self._candy_prepare()
        if current != (self.__width, self.__height):
            self._queue_rendering()
            self._queue_sync_layout()
            return True
        return False

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
            self._candy__parent = _weakref.ref(parent)
        self._candy_prepare()
        if parent:
            self._candy__parent = None

    # clutter rendering

    def _clutter_render(self):
        """
        Render the widget
        """
        raise NotImplemented

    def _clutter_set_obj_size(self, width=None, height=None):
        """
        Set clutter object size to inner or given width and height
        """
        if self.__width is None or self.__height is None:
            self.__calculate_size()
        width = width or self.__width - 2 * self.__xpadding
        height = height or self.__height - 2 * self.__ypadding
        if self.subpixel_precision:
            self._obj.set_sizeu(width, height)
            self._intrinsic_size = width, height
        else:
            self._obj.set_size(int(width), int(height))
            self._intrinsic_size = int(width), int(height)

    def _clutter_sync_layout(self):
        """
        Layout the widget
        """
        self._sync_layout = False
        x, y = self.__x, self.__y
        anchor_x = anchor_y = 0
        if self.__xalign in (Widget.ALIGN_CENTER, Widget.ALIGN_RIGHT):
            obj_width = self.intrinsic_size[0]
            if self.__xalign == Widget.ALIGN_CENTER:
                x += (self.__width - obj_width) / 2
                anchor_x = obj_width / 2
            elif self.__xalign == Widget.ALIGN_RIGHT:
                x += self.__width - obj_width - self.__xpadding
                anchor_x = obj_width
        else:
            x += self.__xpadding
        if self.__yalign in (Widget.ALIGN_CENTER, Widget.ALIGN_BOTTOM):
            obj_height = self.intrinsic_size[1]
            if self.__yalign == Widget.ALIGN_CENTER:
                y += (self.__height - obj_height) / 2
                anchor_y = obj_height / 2
            elif self.__yalign == Widget.ALIGN_BOTTOM:
                y += self.__height - obj_height - self.__ypadding
                anchor_y = obj_height
        else:
            y += self.__ypadding
        if self.__anchor:
            anchor_x, anchor_y = self.__anchor
        if anchor_x or anchor_y:
            if self.subpixel_precision:
                self._obj.set_anchor_pointu(anchor_x, anchor_y)
            else:
                anchor_x = int(anchor_x)
                anchor_y = int(anchor_y)
                self._obj.set_anchor_point(anchor_x, anchor_y)
            x += anchor_x
            y += anchor_y
        if self.subpixel_precision:
            self._obj.set_positionu(x, y)
        else:
            self._obj.set_position(int(x), int(y))

    def _clutter_sync_properties(self):
        """
        Set some simple properties of the clutter.Actor
        """
        if 'parent' in self._sync_properties:
            clutter_parent = self._sync_properties.pop('parent')
            if not clutter_parent:
                # destroy object and return
                import time
                t1 = time.time()
                self._obj.destroy()
                self._obj = None
                if time.time() - t1 > 0.002:
                    print 'delete', self, time.time() - t1
                return False
            if self._obj.get_parent():
                self._obj.get_parent().remove(self._obj)
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
        if 'stack-position' in self._sync_properties:
            self._obj.lower_actor(self._sync_properties['stack-position']._obj)
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
        if self.xalign == self.ALIGN_SHRINK:
            return self.intrinsic_size[0] + 2 * self.__xpadding
        return self.__width

    @width.setter
    def width(self, width):
        if self.__width == width:
            return
        if isinstance(width, str):
            # width is percent of the parent
            self.__dynamic_width = int(width[:-1])
            self.__width = None
        elif width is None:
            # fill the whole parent based on the widget's position
            self.__dynamic_width = -1
            self.__width = None
        else:
            self.__dynamic_width = None
            self.__width = width
        self._dynamic_size = self.__dynamic_width or self.__dynamic_height
        if self._obj is not None:
            self._queue_sync_properties('size')
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
        if self.yalign == self.ALIGN_SHRINK:
            return self.intrinsic_size[1] + 2 * self.__ypadding
        return self.__height

    @height.setter
    def height(self, height):
        if self.__height == height:
            return
        if isinstance(height, str):
            # height is percent of the parent
            self.__dynamic_height = int(height[:-1])
            self.__height = None
        elif height is None:
            # fill the whole parent based on the widget's position
            self.__dynamic_height = -1
            self.__height = None
        else:
            self.__dynamic_height = None
            self.__height = height
        self._dynamic_size = self.__dynamic_width or self.__dynamic_height
        if self._obj is not None:
            self._queue_sync_properties('size')
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
    def intrinsic_size(self):
        if not self._intrinsic_size:
            if self.__width is None or self.__height is None:
                self.__calculate_size()
            return self.__width - 2 * self.__xpadding, self.__height - 2 * self.__ypadding
        return self._intrinsic_size

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
        if self._candy__parent is None:
            return None
        return self._candy__parent()

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

#     def __del__(self):
#         print '__del__', self
