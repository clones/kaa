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
from .. import candyxml, animation, Modifier, backend

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

    @group Context Management: set_context, get_context, try_context, eval_context
    @cvar context_sensitive: class variable for inherting class if the class
        depends on the context.
    """

    #: set if the object reacts on set_context
    context_sensitive = False

    #: template for object creation
    __template__ = Template

    # sync indications
    _sync_required = True
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
    __scale = None
    __depth = 0
    __opacity = 255

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
            self.__width  = size[0] or 0
            self.__height = size[1] or 0
        if pos is not None:
            self.__x, self.__y = pos
        self._sync_properties = {}
        self.__depends = {}
        self.__context = context or {}
        self.userdata = {}

    def get_context(self, key=None):
        """
        Get the context the widget is in.

        @param key: if key is not None return only the value for key
            from the context
        @returns: context dict or value for the key
        """
        if key is None:
            return self.__context
        return self.__context.get(key)

    def set_context(self, context):
        """
        Set a new context.

        @param context: dict of context key,value pairs
        """
        self.__context = context

    def try_context(self, context):
        """
        Check if the widget is capable of the given context based on its
        dependencies. If it is possible set the context.

        @param context: context dict
        @returns: False if the widget can not handle the context or True
        """
        if self.__depends:
            try:
                for var, value in self.__depends.items():
                    if value != repr(eval(var, context)):
                        return False
            except AttributeError:
                return False
        self.set_context(context)
        return True

    def eval_context(self, var, default=None, context=None, depends=True):
        """
        Evaluate the context for the given variable. This function is used by
        widgets to evaluate the context and set their dependencies. It should
        not be called from outside the widget.

        @param var: variable name to eval
        @param default: default return value if var is not found
        @param context: context to search, default is the context set on init
            or by set_context.
        @param depends: if set the true the variable and the value will be stored
            as dependency and try_context will return False if the value changes.
        """
        if var.startswith('$'):
            # strip prefix for variables if set
            var = var[1:]
        context = context or self.__context
        try:
            # try the variable as it is
            value = eval(var, context)
        except AttributeError:
            # not found. Maybe it is an object with a get method.
            # foo.bar.buz could be foo.bar.get('buz')
            for subvar in self.__re_eval.findall(var):
                try:
                    newvar = var.replace(subvar, '.get("%s")' % subvar[1:])
                    value = eval(newvar, context)
                    if value is None:
                        value = default
                except Exception, e:
                    continue
                break
            else:
                log.error('unable to evaluate %s', var)
                return default
        if depends:
            self.__depends[var] = repr(value)
        return value

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
            self.parent._child_restack(self, 'top')

    def lower_bottom(self):
        """
        Lower widget to the bottom of its group.
        """
        if self.parent:
            self.parent._child_restack(self, 'bottom')

    # rendering

    def _queue_sync(self, rendering=False, layout=False):
        """
        Queue rendering or re-layout to be called on the next sync.

        @param rendering: child requires calling _candy_render
        @param layout: child requires calling _candy_sync_layout
        """
        if rendering:
            self._sync_rendering = True
        if layout:
            self._sync_layout = True
        self._sync_required = True
        parent = self.parent
        if parent and not parent._sync_rendering:
            parent._queue_sync(rendering=True)

    def _queue_sync_properties(self, *properties):
        """
        Queue clutter properties to be set on the next sync.
        """
        for prop in properties:
            self._sync_properties[prop] = True
        self._sync_required = True
        parent = self.parent
        if parent and not parent._sync_rendering:
            parent._queue_sync(rendering=True)

    def _candy_sync(self):
        """
        Called from the clutter thread to update the widget.
        """
        self._sync_required = False
        if self._sync_rendering:
            self._sync_rendering = False
            self._candy_render()
        if self._sync_layout:
            self._candy_sync_layout()
        if self._sync_properties:
            self._candy_sync_properties()
            self._sync_properties = {}

    def _candy_render(self):
        """
        Render the widget
        """
        raise NotImplemented

    def _candy_sync_layout(self):
        """
        Layout the widget
        """
        self._sync_layout = False
        x, y = self.__x, self.__y
        if self.__anchor:
            self._obj.set_anchor_point(*self.__anchor)
            x += self.__anchor[0]
            y += self.__anchor[1]
        if self.__xalign:
            if self.__xalign == Widget.ALIGN_CENTER:
                x += (self.__width - self._obj.get_width()) / 2
            if self.__xalign == Widget.ALIGN_RIGHT:
                x += self.__width - self._obj.get_width()
        if self.__yalign:
            if self.__yalign == Widget.ALIGN_CENTER:
                y += (self.__height - self._obj.get_height()) / 2
            if self.__yalign == Widget.ALIGN_BOTTOM:
                y += self.__height - self._obj.get_height()
        self._obj.set_position(x, y)

    def _candy_sync_properties(self):
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
        if 'scale' in self._sync_properties:
            self._obj.set_scale(*self.__scale)
        if 'depth' in self._sync_properties:
            self._obj.set_depth(self.__depth)
        if 'opacity' in self._sync_properties:
            self._obj.set_opacity(self.__opacity)

    # properties

    @property
    def x(self):
        return self.__x

    @x.setter
    def x(self, x):
        self.__x = x
        self._queue_sync(layout=True)

    @property
    def y(self):
        return self.__y

    @y.setter
    def y(self, y):
        self.__y = y
        self._queue_sync(layout=True)

    @property
    def width(self):
        return self.__width

    @width.setter
    def width(self, width):
        if self._obj is not None:
            self._queue_sync_properties('size')
        self.__width = width
        self._queue_sync(rendering=True, layout=True)

    @property
    def height(self):
        return self.__height

    @height.setter
    def height(self, height):
        if self._obj is not None:
            self._queue_sync_properties('size')
        self.__height = height
        self._queue_sync(rendering=True, layout=True)

    @property
    def geometry(self):
        return self.__x, self.__y, self.__width, self.__height

    @property
    def anchor_point(self):
        return self.__anchor or (0, 0)

    @anchor_point.setter
    def anchor_point(self, (x, y)):
        self.__anchor = x, y
        self._queue_sync(layout=True)

    @property
    def xalign(self):
        return self.__xalign or Widget.ALIGN_LEFT

    @xalign.setter
    def xalign(self, align):
        self.__xalign = align
        self._queue_sync(layout=True)

    @property
    def yalign(self):
        return self.__yalign or Widget.ALIGN_TOP

    @yalign.setter
    def yalign(self, align):
        self.__yalign = align
        self._queue_sync(layout=True)

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
    def parent(self):
        if self.__parent is None:
            return None
        return self.__parent()

    @parent.setter
    def parent(self, parent):
        if self.__parent is not None:
            curent = self.__parent()
            if curent is not None:
                curent._child_remove(self)
        self.__parent = None
        if parent:
            self.__parent = _weakref.ref(parent)
            parent._child_add(self)


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
