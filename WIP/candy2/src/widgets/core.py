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
import gtk

# kaa imports
import kaa.imlib2

# kaa.candy imports
import kaa.candy

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
    def __init__(self, cls, **kwargs):
        self._cls = cls
        self._properties = kwargs.pop('properties', None)
        self._kwargs = kwargs
        self.__userdata = {}

    def __call__(self, context=None, **override):
        """
        Create the widget with the given context and override some
        constructor arguments.
        """
        kwargs = self._kwargs
        if override:
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
        log.info('Create %s: %s secs', self._cls.__gui_name__, time.time() - t1)
        return widget

    def get_userdata(self, key):
        """
        Get additional data stored in this object.
        """
        return self.__userdata.get(key)

    def set_userdata(self, key, value):
        """
        Store additional data in this object.
        """
        self.__userdata[key] = value

    def get_attribute(self, attr):
        """
        Get the value for the attribute for object creation.
        """
        return self._kwargs.get(attr)

    def set_property(self, key, *value):
        """
        Set a property for the template. The properties will be set after the
        object is created.
        """
        if self._properties is None:
             self._properties = kaa.candy.Properties()
        self._properties[key] = value

    @classmethod
    def get_class_from_XML(cls, element):
        """
        Get the class for the XML element
        """
        return kaa.candy.xmlparser.get_class(element.node, element.style)

    @classmethod
    def from_XML(cls, element):
        """
        Parse the XML element for parameter and create a Template.
        """
        properties = element.properties
        if properties is not None:
            element.remove(properties)
            properties = kaa.candy.Properties.from_XML(properties)
        animations = {}
        for child in element.get_children('define-animation'):
            element.remove(child)
            animations[child.style] = child.xmlcreate()
        widget = cls.get_class_from_XML(element)
        if widget is None:
            log.error('undefined widget %s:%s', element.node, element.style)
        kwargs = widget.parse_XML(element)
        kwargs['properties'] = properties
        template = cls(widget, **kwargs)
        if animations:
            template.set_property('animations', animations)
        return template


class Widget(object):
    """
    Basic widget. All widgets from the backend must inherit from it.
    """

    #: set if the object reacts on set_context
    context_sensitive = False

    #: template for object creation
    __template__ = Template

    def __init__(self, pos=None, size=None, context=None):
        """
        Basic widget constructor
        """
        if size is not None:
            if size[0] is not None:
                self.set_width(size[0])
            if size[1] is not None:
                self.set_height(size[1])
        if pos is not None:
            self.set_position(*pos)
        # FIXME: make _depends private
        self._depends = []
        self.__animations = []
        self.__context = context
        self.__userdata = {}

    def set_parent(self, parent):
        """
        Set the parent widget
        """
        if self.get_parent():
            self.get_parent().remove(self)
        if parent:
            parent.add(self)

    def unparent(self):
        """
        Remove the widget
        """
        if self.get_parent():
            self.get_parent().remove(self)
        
    def get_context(self, key=None):
        """
        Get the context the widget is in.
        """
        if key is None:
            return self.__context
        return self.__context.get(key)

    def set_context(self, context):
        """
        Set a new context.
        """
        self.__context = context

    def try_context(self, context):
        """
        Check if the widget is capable of the given context based on its
        dependencies and return False if not or set the context and return
        True if it is.
        """
        for var, value in self._depends:
            if value != eval(var, context):
                return False
        self.set_context(context)
        return True

    def set_dependency(self, *dependencies):
        """
        Set list of dependencies this widget has based on the context.
        """
        self._depends = [ (str(d), eval(str(d), self.__context)) for d in dependencies ]

    def set_animations(self, animations):
        """
        Set additional animations for object.animate()
        """
        self.__animations = animations

    def get_userdata(self, key):
        """
        Get additional data stored in this object.
        """
        return self.__userdata.get(key)

    def set_userdata(self, key, value):
        """
        Store additional data in this object.
        """
        self.__userdata[key] = value

    def animate(self, name, *args, **kwargs):
        """
        Animate the object with the given animation.
        """
        if name in self.__animations:
            return self.__animations[name](self)
        a = kaa.candy.animation.get(name)
        if a:
            return a(self, *args, **kwargs)
        if not name in ('hide', 'show'):
            log.error('no animation named %s', name)

    @classmethod
    def create_template(cls, **kwargs):
        """
        Create a template for this class.
        """
        return cls.__template__(cls, **kwargs)

    @classmethod
    def parse_XML(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        return XMLDict(pos=element.pos, size=(element.width, element.height))

    # def __del__(self):
    #     print '__del__', self


class Group(Widget, clutter.Group):
    """
    Group widget.
    """
    def __init__(self, pos=None, size=None, context=None):
        clutter.Group.__init__(self)
        Widget.__init__(self, pos, size, context)
        self._max_size = size

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
        """
        if visible:
            child.show()
        super(Group, self).add(child)


class Texture(Widget, clutter.Texture):
    """
    Clutter Texture widget.
    """
    def __init__(self, pos=None, size=None, context=None):
        clutter.Texture.__init__(self)
        Widget.__init__(self, pos, size, context)

    def set_from_file(self, filename):
        """
        Set content based on a filename.
        """
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        self.set_pixbuf(pixbuf)


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
        super(Imlib2Texture, self).__init__(pos, size, context)
        self._image = kaa.imlib2.new(size)

    def imlib2_create(self):
        """
        Return Imlib2 context image.
        """
        return Imlib2Texture.Context(self, self._image._image)


class CairoTexture(Widget, clutter.cluttercairo.CairoTexture):
    """
    Cairo based Texture widget,
    """
    def __init__(self, pos, size, context=None):
        clutter.cluttercairo.CairoTexture.__init__(self, *size)
        Widget.__init__(self, pos, None, context)

    def clear(self):
        """
        Clear the complete surface
        """
        context = self.cairo_create()
        context.set_operator(cairo.OPERATOR_CLEAR)
        context.set_source_rgba(255,255,255,255)
        context.paint()
        del context
