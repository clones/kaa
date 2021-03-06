# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# candyxml.py - Parser to parse XML into widget Templates
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008-2009 Dirk Meyer, Jason Tackaberry
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

__all__ = [ 'parse', 'register', 'get_class' ]

# python imports
import os
import logging
import xml.sax

# kaa.candy imports
import core

# get logging object
log = logging.getLogger('kaa.candy')

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
        if key in ('x', 'xpadding'):
            value = int(scale[0] * int(value))
        elif key in ('y', 'ypadding'):
            value = int(scale[1] * int(value))
        elif key == 'width' and not value.endswith('%'):
                x1 = int(scale[0] * int(attrs.get('x', 0)))
                x2 = int(scale[0] * (int(attrs.get('x', 0)) + int(value)))
                value = x2 - x1
        elif key == 'height' and not value.endswith('%'):
            y1 = int(scale[1] * int(attrs.get('y', 0)))
            y2 = int(scale[1] * (int(attrs.get('y', 0)) + int(value)))
            value = y2 - y1
        elif key in ('radius', 'size', 'spacing'):
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
        return self._children[:].__iter__()

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
            # Set width or height to None. All widgets except the grid will
            # accept such values. The real value will be inserted later
            # based on the parent settings
            return None
        return None

    def xmlcreate(element):
        """
        Create a template or object from XML.
        """
        parser = _parser.get(element.node)
        if parser is None:
            raise RuntimeError('no parser for %s' % element.node)
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
    def __init__(self, data, geometry, elements=None):
        xml.sax.ContentHandler.__init__(self)
        self._elements = elements or ElementDict()
        # Internal stuff
        self._scale = None
        self._geometry = geometry
        self._root = None
        self._current = None
        self._stack = []
        self._names = []
        self._parser = xml.sax.make_parser()
        self._parser.setContentHandler(self)
        if data.find('<') >= 0:
            # data is xml data
            self._parser.feed(data)
        else:
            # data is filename
            self._parser.parse(data)

    def get_elements(self):
        """
        Return root attributes and parsed elements
        """
        if self._root[0] == '__candyxml_simple__':
            # fake candyxml tree, only one element
            return self._elements.values()[0].values()[0]
        return dict(self._root[1]), self._elements

    def startElement(self, name, attrs):
        """
        SAX Callback.
        """
        if self._root is None:
            self._root = name, attrs
            self._scale = 1.0, 1.0
            if attrs.get('geometry'):
                # candyxml tag has geometry information for scaling
                w, h = [ int(v) for v in attrs['geometry'].split('x') ]
                self.width, self.height = w, h
                if self._geometry:
                    self._scale = float(self._geometry[0]) / w, float(self._geometry[1]) / h
            else:
                # no geometry information. Let us hope we have something from the stage
                if not self._geometry:
                    raise RuntimeError('no geometry information')
                self.width, self.height = self._geometry
            if not name in _parser.keys():
                # must be a parent tag like cnadyxml around
                # everything. This means we may have more than one
                # widget in this xml stream.
                return
            # create fake root
            self._root = '__candyxml_simple__', {}
        if name == 'alias' and len(self._stack) == 0:
            self._names.append(attrs['name'])
            return
        element = Element(name, self._current or self, attrs, self._scale)
        if self._current is not None:
            self._stack.append(self._current)
            self._current._children.append(element)
        else:
            self._names.append(attrs.get('name'))
        self._current = element

    def endElement(self, name):
        """
        SAX Callback.
        """
        if self._current:
            self._current.content = self._current.content.strip()
        if len(self._stack):
            self._current = self._stack.pop()
        elif name == 'alias':
            # alias for high level element, skip
            return
        elif name != self._root[0]:
            screen = self._current.xmlcreate()
            if not self._elements.get(name):
                self._elements[name] = ElementDict()
            for subname in self._names:
                self._elements[name][subname] = screen
            self._current = None
            self._names = []

    def characters(self, c):
        """
        SAX callback
        """
        if self._current:
            self._current.content += c


def parse(data, size=None, elements=None):
    """
    Load a candyxml file based on the given screen resolution.
    @param data: filename of the XML file to parse or XML data
    @param size: width and height of the window to adjust values in the XML file
    @returns: root element attributes and dict of parsed elements
    """
    if not os.path.isdir(data):
        return CandyXML(data, size, elements).get_elements()
    attributes = {}
    for f in os.listdir(data):
        if not f.endswith('.xml'):
            continue
        f = os.path.join(data, f)
        try:
            a, elements = CandyXML(f, size, elements).get_elements()
            attributes.update(a)
        except Exception, e:
            log.exception('parse error in %s', f)
    return attributes, elements

class Styles(dict):
    """
    Style dict for candyxml_parse and candyxml_create callbacks
    """
    def candyxml_parse(self, element):
        return self.get(element.style)

#: list of candyxml parser
_parser = {}

def register(cls):
    """
    Register a class
    """
    name = cls.candyxml_name
    parser = _parser
    if not isinstance(cls, Styles):
        if not name in parser:
            parser[name] = Styles()
        parser, name = parser[name], getattr(cls, 'candyxml_style', None)
    if name in parser:
        raise RuntimeError('%s already registered' % name)
    parser[name] = cls

def get_class(name, style):
    """
    Get the class registered to the given name and style
    """
    return _parser.get(name).get(style)
