# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - Core Widgets and Template
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

__all__ = [ 'Widget', 'Group', 'Texture', 'Imlib2Texture', 'CairoTexture']

# python imports
import logging
import time

# clutter imports
import clutter
import clutter.cluttercairo
import pango
import cairo

# kaa imports
import kaa.imlib2

# kaa.candy imports
from .. import candyxml, animation, Properties, threaded

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
        self._properties = kwargs.pop('properties', None)
        self._kwargs = kwargs
        self.__userdata = {}

    def __call__(self, context=None, **override):
        """
        Create the widget with the given context and override some
        constructor arguments.
        @param context: context to create the widget in
        @param override: override the given keyword arguments on creation
        @returns: widget object
        """
        kwargs = self._kwargs
        if override:
            # FIXME: this part is kind of ugly
            kwargs = self._kwargs.copy()
            for key, value in override.items():
                if key == 'x':
                    kwargs['pos'] = value, kwargs['pos'][1]
                elif key == 'y':
                    kwargs['pos'] = kwargs['pos'][0], value
                elif key == 'width':
                    kwargs['size'] = value, kwargs['size'][1]
                elif key == 'height':
                    kwargs['size'] = kwargs['size'][0], value
                else:
                    kwargs[key] = value
        t1 = time.time()
        if self._cls.context_sensitive:
            kwargs['context'] = context
        try:
            widget = self._cls(**kwargs)
        except TypeError, e:
            log.exception('error creating %s%s', self._cls, kwargs.keys())
            return None
        if self._properties:
            self._properties.apply(widget)
        log.info('Create %s: %s secs', self._cls.candyxml_name, time.time() - t1)
        return widget

    def get_userdata(self, key):
        """
        Get additional data stored in this object.
        @param key: key of the userdata
        @returns: value or None if not set
        """
        return self.__userdata.get(key)

    def set_userdata(self, key, value):
        """
        Store additional data in this object. This function can be used if additional
        information should be stored in a template for later reference. The userdata
        is not copied to a created widget.
        @param key: key to name the userdata
        @param value: value of the userdata.
        """
        self.__userdata[key] = value

    def get_attribute(self, attr):
        """
        Get the value for the attribute for object creation.
        @param attr: attribute name for cls.__init__
        @returns: attribute value or None if not set
        """
        return self._kwargs.get(attr)

    def set_property(self, key, *value):
        """
        Set a property for the template. The properties will be set after the
        object is created.
        """
        if self._properties is None:
             self._properties = Properties()
        self._properties[key] = value

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
        properties = element.properties
        if properties is not None:
            element.remove(properties)
            properties = Properties.candyxml_create(properties)
        animations = {}
        # FIXME: rewrite animation support
        for child in element.get_children('define-animation'):
            element.remove(child)
            animations[child.style] = child.xmlcreate()
        widget = cls.candyxml_get_class(element)
        if widget is None:
            log.error('undefined widget %s:%s', element.node, element.style)
        kwargs = widget.candyxml_parse(element)
        kwargs['properties'] = properties
        template = cls(widget, **kwargs)
        if animations:
            template.set_property('animations', animations)
        return template


class Widget(object):
    """
    Basic widget. All widgets from the backend must inherit from it.
    @group Context Management: set_context, get_context, try_context, set_dependency
    @group Animations: animate, stop_animations, set_animations
    @cvar context_sensitive: class variable for inherting class if the class
        depends on the context.
    """

    #: set if the object reacts on set_context
    context_sensitive = False

    #: template for object creation
    __template__ = Template

    def __init__(self, pos=None, size=None, context=None):
        """
        Basic widget constructor.
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param context: the context the widget is created in
        """
        if size is not None:
            if size[0] is not None:
                self.set_width(size[0])
            if size[1] is not None:
                self.set_height(size[1])
        if pos is not None:
            self.set_position(*pos)
        # animations running created by self.animate()
        self._running_animations = {}
        # FIXME: make _depends private
        self._depends = []
        self.__animations = []
        self.__context = context
        self.__userdata = {}

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
        for var, value in self._depends:
            if value != eval(var, context):
                return False
        self.set_context(context)
        return True

    def set_dependency(self, *dependencies):
        """
        Set list of dependencies this widget has based on the context. This function
        is used internally in a widget implementation.
        @param dependencies: list of keys of the context this widget requires to
           be set to the same values as they were when the widget was created.
        """
        try:
            self._depends = [ (str(d), eval(str(d), self.__context)) \
                              for d in dependencies ]
        except Exception, e:
            log.error('bad dependencies: %s in context %s for %s', dependencies,
                      self.__context, self)

    def set_animations(self, animations):
        """
        Set additional animations for object.animate()
        @param animations: dict with key,Animation
        """
        self.__animations = animations

    @threaded()
    def animate(self, name, *args, **kwargs):
        """
        Animate the object with the given animation. The animations are defined
        by C{set_animations}, the candyxml definition or the basic animation
        classes in kaa.candy.animation. Calling this function is thread-safe.
        @param name: name of the animation used by C{set_animations} or
            kaa.candy.animations
        """
        # FIXME: rewrite animation code
        if name in self.__animations:
            return self.__animations[name](self, *args, **kwargs)
        a = animation.get(name)
        if a:
            return a(self, *args, **kwargs)
        if not name in ('hide', 'show'):
            log.error('no animation named %s', name)

    def stop_animations(self):
        """
        Stop all running animations for the widget. This function must be called
        when a widget is removed from the stage. Calling C{destroy} will also
        stop all animations.
        """
        for animation in self._running_animations.values():
            animation._clutter_stop()

    def set_parent(self, parent):
        """
        Set the parent widget.
        @param parent: kaa.candy Group or Stage object
        """
        if self.get_parent():
            self.get_parent().remove(self)
        parent.add(self)

    def destroy(self):
        """
        Destroy the widget. This function _must_ be called when animations
        running in the widget to stop them first.
        """
        for animation in self._running_animations.values():
            animation._clutter_stop()
        parent = self.get_parent()
        if parent is not None:
            parent.remove(self)

    def get_userdata(self, key):
        """
        Get additional data stored in this object.
        @param key: key of the userdata
        @returns: value or None if not set
        """
        return self.__userdata.get(key)

    def set_userdata(self, key, value):
        """
        Store additional data in this object. This function can be used if additional
        information should be stored in a widget for later reference.
        @param key: key to name the userdata
        @param value: value of the userdata.
        """
        self.__userdata[key] = value

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
        return XMLDict(pos=element.pos, size=(element.width, element.height))

    @classmethod
    def candyxml_register(cls, style=None):
        """
        Register class to candyxml. This function can only be called
        once when the class is loaded.
        """
        candyxml.register(cls, style)

    # def __del__(self):
    #     print '__del__', self


class Group(Widget, clutter.Group):
    """
    Group widget.
    """
    def __init__(self, pos=None, size=None, context=None):
        """
        Simple clutter.Group widget
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None. A clutter.Group
            does not respect the given geometry. If set, the geometry can be
            read with the get_max memeber functions.
        @param context: the context the widget is created in
        """
        clutter.Group.__init__(self)
        Widget.__init__(self, pos, size, context)
        self._max_size = size or (None, None)

    def get_max_size(self):
        """
        Return maximum available size
        """
        return self._max_size

    def get_max_width(self):
        """
        Return maximum available width
        """
        return self._max_size[0]

    def get_max_height(self):
        """
        Return maximum available height
        """
        return self._max_size[1]

    def add(self, child, visible=True):
        """
        Add a child and set it visible.
        @param child: kaa.candy.Widget, NOT a Template
        @param visible: set the child status to visible when adding
        """
        if visible:
            child.show()
        super(Group, self).add(child)

    def destroy(self):
        """
        Destroy the group and all children. The object is removed from the
        parant and not usable anymore.
        """
        for child in self.get_children():
            child.destroy()
        super(Group, self).destroy()


class Texture(Widget, clutter.Texture):
    """
    Clutter Texture widget.
    """
    def __init__(self, pos=None, size=None, context=None):
        """
        Simple clutter.Texture widget
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param context: the context the widget is created in
        """
        clutter.Texture.__init__(self)
        Widget.__init__(self, pos, size, context)


class Imlib2Texture(Texture):
    """
    Imlib2 based Texture widget.
    """
    class Context(kaa.imlib2.Image):
        """
        Imlib2 context to draw on.
        """
        def __init__(self, texture, image):
            super(Imlib2Texture.Context, self).__init__(image)
            self.__texture = texture

        def __del__(self):
            """
            Redraw clutter Texture object.
            """
            self.__texture.set_from_rgb_data(self.get_raw_data(), True,
                  self.width, self.height, 1, 4, 0)

    def __init__(self, pos, size, context=None):
        """
        Create a kaa.imlib2 based texture.
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget
        @param context: the context the widget is created in
        """
        super(Imlib2Texture, self).__init__(pos, size, context)
        self._image = kaa.imlib2.new(size)

    def imlib2_create(self):
        """
        Return Imlib2 context image. The widget will update once the returned
        kaa.imlib2 Image is deleted.
        """
        return Imlib2Texture.Context(self, self._image._image)


class CairoTexture(Widget, clutter.cluttercairo.CairoTexture):
    """
    Cairo based Texture widget.
    """
    def __init__(self, pos, size, context=None):
        """
        Create a cairo based texture.
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget
        @param context: the context the widget is created in
        """
        clutter.cluttercairo.CairoTexture.__init__(self, *size)
        Widget.__init__(self, pos, None, context)

    def clear(self):
        """
        Clear the complete surface. This function may be called by an
        inheriting class in a render function on update.
        """
        context = self.cairo_create()
        context.set_operator(cairo.OPERATOR_CLEAR)
        context.set_source_rgba(255,255,255,255)
        context.paint()
        del context
