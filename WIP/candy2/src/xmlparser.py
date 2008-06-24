# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# xmlparser.py - Parser to parse XML text into widget Templates
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

__all__ = [ 'parse', 'register', 'get_class' ]

# python imports
import xml.sax

# kaa.candy imports
import core

class MagicDict(dict):

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
    def __init__(self, node, attrs, scale):
        self.content = ''
        self.node = node
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
        value = self._attrs.get(attr)
        if value is not None:
            return value
        for child in self._children:
            if child.node == attr:
                return child
        return None

    def xmlcreate(element):
        """
        Create a template or object from XML.
        """
        parser = _parser.get(element.node)
        if isinstance(parser, dict):
            parser = parser.parse_XML(element)
        if parser is None:
            raise RuntimeError('no parser for %s:%s' % (element.node, element.style))
        return getattr(parser, '__template__', parser).from_XML(element)

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


class Theme(xml.sax.ContentHandler):
    """
    XML theme parser.
    """
    def __init__(self, theme, geometry):
        xml.sax.ContentHandler.__init__(self)
        self.screens = MagicDict()
        # Internal stuff
        self._scale = None
        self._geometry = geometry
        self._current = None
        self._stack = []
        self._parser = xml.sax.make_parser()
        self._parser.setContentHandler(self)
        self._parser.parse(theme)

    def startElement(self, name, attrs):
        """
        SAX Callback.
        """
        if self._current is None and name == 'theme':
            g = attrs['geometry'].split('x')
            self._scale = float(self._geometry[0]) / int(g[0]), \
                          float(self._geometry[1]) / int(g[1])
            return
        element = Element(name, attrs, self._scale)
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
        elif name != 'theme':
            screen = self._current.xmlcreate()
            if not self.screens.get(name):
                self.screens[name] = MagicDict()
            self.screens[name][self._current.name] = screen
            self._current = None

    def characters(self, c):
        """
        SAX callback
        """
        if self._current:
            self._current.content += c


def parse(theme, (width, height)):
    """
    Load a theme XML file based on the given screen resolution.
    """
    return Theme(theme, (width, height)).screens

class Styles(dict):
    def parse_XML(self, element):
        return self.get(element.style)
        
_parser = {}

def register(cls, style=None):
    """
    Register a class with the given style.
    """
    name = cls.__gui_name__
    style = style or getattr(cls, '__gui_style__', None)
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
    """
    result = _parser.get(name)
    if isinstance(result, dict):
        return result.get(style)
    return result
