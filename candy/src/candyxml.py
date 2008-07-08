# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# candyxml.py - Parser to parse XML into widget Templates
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

"""
XML based scripting language for kaa.candy

CandyXML is an XML based way to define widgets dependencies not using Python
code. It may be used to define themes for applications. It is more powerful
than clutter script and can be extended with application specific widgets.

Widget Definition
=================

The basic idea is that every widget has a name to be used in an XML file. This
is done by the class variable C{candyxml_name} of each widget class. This name
may be unique. If it is not, C{candyxml_style} must also be defined so the parser
knows which class to use on object creation. Each widget must provide a
C{candyxml_parse} function how to parse the XML attributes and subnodes to
arguments that can be used to create an object of that class. The class then
must be registered to candyxml with the C{register} class member function.

Example::
  class Foo(kaa.candy.Widget):
      candyxml_name = 'foo'
      @classmethod
      def candyxml_parse(cls, element):
          ...

  class SimpleBar(kaa.candy.Widget):
      candyxml_name = 'bar'
      candyxml_style = 'simple'
      @classmethod
      def candyxml_parse(cls, element):
          ...

  class ComplexBar(kaa.candy.Widget):
      candyxml_name = 'bar'
      candyxml_style = 'complex'
      @classmethod
      def candyxml_parse(cls, element):
          ...

  # register
  Foo.candyxml_register()
  SimpleBar.candyxml_register()
  ComplexBar.candyxml_register()

XML example::
  <foo .../>                   --> Foo()
  <bar style='simple' .../>    --> SimpleBar()
  <bar style='complex' .../>   --> ComplexBar()

See the kaa.candy L{widgets} about additional details how to write the Python
part and see the C{candyxml_parse} documentation of each widget about how
to use that widget in an XML file.

XML File Parsing
================

The root element of the XML file can be chosen by the application. It must
have width and height attributes and you must also provide width and height
for the parsing function. If they do not match, some values like position
and size of the widgets are changed on parsing. This makes it possible to
define a theme in 800x600 and use it at a window with 1024x768.

The subnodes of the root element can be created using the template system. Each
of these subnodes must have a unique name attribute. The C{parse} function will
return a dict with these names and the template objects to create the widgets.
The XML parser will not create widgets, it only creates templates. This makes
the code thread-safe, you can parse a file from the mainloop and at start of
your application. Note: if the name contains a minus it is converted into an
underscore.

XML Example::
  <xandyxml width='800' height='600'>
      <container name='many-bars'>
          <bar x='10' y='0' style='simple' .../>
          <bar x='10' y='100' style='complex' .../>
      </container>
      <foo name='one-foo' .../>
      <foo name='something' .../>
  </candyxml>

Usage in Python::
  attr, elements = kaa.candy.candyxml.parse(filename, (1024, 768))
  stage.add(elements.container.many_bars)
  stage.add(elements.foo.one_foo)
  stage.add(elements.foo.something)

You can add templates instead of widgets to a stage from the mainloop. A
container does support neither templates nor is it thread-safe. In that
case you need a functions decorated with the C{threaded} decorator.

Example::
  @kaa.candy.threaded():
  def add_stuff():
      container = kaa.candy.Container()
      container.add(elements.foo.one_foo())
      container.set_parent(stage)

Context
=======

In some cases you do not know all attributes of the widget when writing the XML
file, e.g. an image should show the image defined by the C{filename} attribute
of an object you create during runtime. kaa.candy has support for creating
widgets based on a context. Changing the context may change the whole window
with one command. The concept is to split the logic into three parts:
the layout (candyxml), the content (context) and the application logic (your code).
For images and text widgets the magic key is C{$}. See the documentation of the
specific widgets if they are context sensitive or not.

XML Example::
  <xandyxml width='800' height='600'>
      <container name='test'>
          <image filename='$background'/>
          <image filename='$item.filename'/>
      </container>
  </candyxml>

Python Code::
  # context to use, MyImage has a memeber variable filename
  context = dict(background='bg.jpg', item=MyImage())
  # create container widget based on the context.
  container = elements.container.test(context=context)
  ...
  # change item and this will change item.filename
  context['item'] = MyImage2()
  # change the container, this will replace the second image
  container = elements.container.test(context=context)

This makes creating application specific themes very easy. You can define new
widgets for your application. E.g. an audio player: define where to draw the
cover, title, etc and every time a new track starts you can set a new context and
the whole GUI will redraw on its own.
"""

__all__ = [ 'parse', 'register', 'get_class' ]

# python imports
import xml.sax

# kaa.candy imports
import core

class ElementDict(dict):

    def __getattr__(self, attr):
        return self.get(attr)

def scale_attributes(attrs, scale):
    """
    Scale attributes based on the screen geometry
    """
    calc_attrs = {}
    for key, value in attrs.items():
        # FIXME: make sure a value > 0 is always > 0 even after scaling
        if key == 'x':
            value = int(scale[0] * int(value))
        elif key == 'y':
            value = int(scale[1] * int(value))
        elif key == 'width':
            x1 = int(scale[0] * int(attrs.get('x', 0)))
            x2 = int(scale[0] * (int(attrs.get('x', 0)) + int(value)))
            value = x2 - x1
        elif key == 'height':
            y1 = int(scale[1] * int(attrs.get('y', 0)))
            y2 = int(scale[1] * (int(attrs.get('y', 0)) + int(value)))
            value = y2 - y1
        elif key in ('radius', 'size'):
            value = int(scale[1] * int(value))
        elif key.find('color') != -1:
            value = core.Color(value)
        elif key.find('font') != -1:
            value = core.Font(value)
            value.size = int(scale[1] * value.size)
        calc_attrs[str(key).replace('-', '_')] = value
    return calc_attrs


class Element(object):
    """
    XML node element.
    """
    def __init__(self, node, parent, attrs, scale):
        self.content = ''
        self.node = node
        # note: circular reference
        self._parent = parent
        self._scale = scale
        self._attrs = scale_attributes(attrs, scale)
        self._children = []

    def __iter__(self):
        """
        Iterate over the list of children.
        """
        return self._children.__iter__()

    def __getitem__(self, pos):
        """
        Return nth child.
        """
        return self._children[pos]

    def __getattr__(self, attr):
        """
        Return attribute or child with the given name.
        """
        if attr == 'pos':
            return [ self._attrs.get('x', 0), self._attrs.get('y', 0) ]
        if attr == 'size':
            return self.width, self.height
        value = self._attrs.get(attr)
        if value is not None:
            return value
        for child in self._children:
            if child.node == attr:
                return child
        if attr in ('width', 'height'):
            # get width or height from parent
            return getattr(self._parent, attr)
        return None

    def xmlcreate(element):
        """
        Create a template or object from XML.
        """
        parser = _parser.get(element.node)
        if isinstance(parser, dict):
            parser = parser.candyxml_parse(element)
        if parser is None:
            raise RuntimeError('no parser for %s:%s' % (element.node, element.style))
        return getattr(parser, '__template__', parser).candyxml_create(element)

    def get_children(self, node=None):
        """
        Return all children with the given node name
        """
        if node is None:
            return self._children[:]
        return [ c for c in self._children if c.node == node ]

    def attributes(self):
        """
        Get key/value list of all attributes.,
        """
        return self._attrs.items()

    def remove(self, child):
        """
        Remove the given child element.
        """
        self._children.remove(child)

    def get_scale_factor(self):
        """
        Return scale factor for geometry values.
        """
        return self._scale

    def get_scaled(self, attr, pos, type):
        """
        Get attribute scaled.
        """
        return type(self._scale[0] * type(self._attrs.get(attr.replace('-', '_'))))

class CandyXML(xml.sax.ContentHandler):
    """
    candyxml parser.
    """
    def __init__(self, data, geometry):
        xml.sax.ContentHandler.__init__(self)
        self._elements = ElementDict()
        self.width = geometry[0]
        self.height = geometry[1]
        # Internal stuff
        self._scale = None
        self._geometry = geometry
        self._root = None
        self._current = None
        self._stack = []
        self._parser = xml.sax.make_parser()
        self._parser.setContentHandler(self)
        if data.find('<') >= 0:
            # data is xml data
            self._parser.feed(data)
        else:
            # data is filename
            self._parser.parse(data)

    def get_elemets(self):
        """
        Return root attributes and parsed elements
        """
        return self._root[1], self._elements

    def startElement(self, name, attrs):
        """
        SAX Callback.
        """
        if self._root is None:
            self._root = name, attrs
            g = attrs['geometry'].split('x')
            self._scale = float(self._geometry[0]) / int(g[0]), \
                          float(self._geometry[1]) / int(g[1])
            return
        element = Element(name, self._current or self, attrs, self._scale)
        if self._current is not None:
            self._stack.append(self._current)
            self._current._children.append(element)
        self._current = element

    def endElement(self, name):
        """
        SAX Callback.
        """
        if self._current:
            self._current.content = self._current.content.strip()
        if len(self._stack):
            self._current = self._stack.pop()
        elif name != self._root[0]:
            screen = self._current.xmlcreate()
            if not self._elements.get(name):
                self._elements[name] = ElementDict()
            self._elements[name][self._current.name] = screen
            self._current = None

    def characters(self, c):
        """
        SAX callback
        """
        if self._current:
            self._current.content += c


def parse(data, size):
    """
    Load a candyxml file based on the given screen resolution.
    @param data: filename of the XML file to parse or XML data
    @param size: width and height of the window to adjust values in the XML file
    @returns: root element attributes and dict of parsed elements
    @todo: support size=None
    """
    return CandyXML(data, size).get_elemets()


class Styles(dict):
    """
    Style dict for candyxml_parse and candyxml_create callbacks
    """
    def candyxml_parse(self, element):
        return self.get(element.style)

#: list of candyxml parser
_parser = {}

def register(cls, style=None):
    """
    Register a class with the given style.
    @param cls: class with candyxml variables and functions
    @param style: optional style if there is more than one parser for the node
    """
    name = cls.candyxml_name
    style = style or getattr(cls, 'candyxml_style', None)
    parser = _parser
    if style is not None:
        if not name in parser:
            parser[name] = Styles()
        parser, name = parser[name], style
    if name in parser:
        raise RuntimeError('%s already registered' % name)
    parser[name] = cls

def get_class(name, style=None):
    """
    Get the class registered to the given name.
    @param name: parser name
    @param style: style of the parser if there is more than one for the name
    @returns: class of the parser (e.g. Widget)
    """
    result = _parser.get(name)
    if isinstance(result, dict):
        return result.get(style)
    return result
