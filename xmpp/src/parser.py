# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# parser.py - Parser interface for the SAX stream parser
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.xmpp - XMPP framework for the Kaa Media Repository
# Copyright (C) 2008 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
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

"""
XML stream parser
"""

__all__ = [ 'Callbacks', 'stanza', 'parser', 'message', 'iq',
            'ElementParser', 'XMLStreamParser' ]

# python imports
import logging
import xml.sax

# kaa imports
import kaa

# kaa.xmpp imports
import element

# get logging object
log = logging.getLogger('xmpp')

def _dynamic_connect(identifier):
    """
    Create a decorator with the given identifier.
    """
    identifier = '_xmpp_' + identifier
    def connect(name=None, xmlns=None, coroutine=False):
        """
        Decorator that marks the decorated function with the given identifier
        set to the node name and the xml namespace.
        """
        def decorator(func):
            if coroutine:
                func = kaa.coroutine()(func)
            nodename = name
            if nodename is None:
                nodename = func.func_name
                if nodename.startswith('_handle_'):
                    nodename = nodename[8:]
                if nodename.startswith('_'):
                    nodename = nodename[1:]
            setattr(func, identifier, (nodename, xmlns))
            return func
        return decorator
    return connect

# decorator for <stanza> callbacks
stanza = _dynamic_connect('stanza')
# decorator for parser callbacks
parser = _dynamic_connect('parser')
# decorator for <message> callbacks
message = _dynamic_connect('message')
# decorator for <iq> callbacks
iq = _dynamic_connect('iq')

class Callbacks(object):
    """
    Class for storing callbacks for the given identifier.
    """
    def __init__(self, identifier):
        self._dict = {}
        self._identifier = '_xmpp_'+ identifier

    def _list_callbacks(self, obj):
        """
        Return all callbacks from the given object.
        """
        result = []
        for var in dir(obj.__class__):
            if isinstance(getattr(obj.__class__, var), property):
                continue
            func = getattr(obj, var)
            info = getattr(func, self._identifier, None)
            if info:
                result.append((func,) + info)
        return result

    def connect(self, obj, jid=None):
        """
        Connect an functions from an object based on name and namespace.
        An optional argument jid can be used to connect different
        callbacks for the same stanza based on the jid.
        """
        for func, name, xmlns in self._list_callbacks(obj):
            # register callback
            key = '%s::%s::%s' % (xmlns, name, jid)
            if key in self._dict:
                raise RuntimeError('%s already connected' % key)
            self._dict[key] = func

    def disconnect(self, obj, jid=None):
        """
        Disconnect a callback connected with the given arguments.
        """
        for func, name, xmlns in self._list_callbacks(obj):
            # register callback
            del self._dict['%s::%s::%s' % (xmlns, name, jid)]

    def get(self, name, xmlns, jid=None):
        """
        Return the callback for the given node name, namespace and jid. If
        no callback is found, return a callback without the jid argument.
        If still no callback is found, return None.
        """
        if jid is None:
            return self._dict.get('%s::%s::%s' % (xmlns, name, None), None)
        r = self._dict.get('%s::%s::%s' % (xmlns, name, jid), None)
        if r is not None:
            return r, True
        return self._dict.get('%s::%s::%s' % (xmlns, name, None), None), False


class ElementParser(object):
    """
    A SAXParser that creates a tree of Element objects.
    """

    def __init__(self, name, xmlns, attr):
        self.node = self._create_node(name, xmlns, saxattributes=attr)
        self.stack = [ self.node ]

    def _create_node(self, name, xmlns, saxattributes):
        attr = {}
        for (ns, key), value in saxattributes.items():
            attr[str(key)] = value
        return element.Element(name, xmlns, **attr)

    def start_element(self, name, xmlns, attr):
        """
        SAX callback when an element starts.
        """
        if not self.stack:
            node = self._create_node(name, xmlns, saxattributes=attr)
            self.node = node
        else:
            if self.stack[-1].xmlns == xmlns:
                node = self._create_node(name, None, saxattributes=attr)
            else:
                node = self._create_node(name, xmlns, saxattributes=attr)
            self.stack[-1].append(node)
        self.stack.append(node)

    def end_element(self, name, xmlns):
        """
        SAX callback when an element ends.
        """
        self.stack.pop()

    def parsed_element(self, name, xmlns, element):
        """
        SAX callback when an element is parsed by a different SAXParser.
        """
        self.stack[-1].append(element)

    def characters(self, c):
        """
        SAX callback for character data.
        """
        self.stack[-1]._content += c

    def get_result(self):
        """
        SAX callback at the end to return the object parsed by the parser.
        The returned object can be any kind of object, it only needs a 'name'
        attribute to represent the root element this parser was created for.
        """
        return self.node


class XMLStreamParser(xml.sax.ContentHandler):
    """
    SAX parser for an XML stream used for XMPP. If an XMPP stream is restarted
    the parser becomes invalid and a new instance must be created.
    """

    # parser callback plugin list
    saxparser = Callbacks('parser')

    def __init__(self, callback):
        self.signals = kaa.Signals('invalid')
        xml.sax.ContentHandler.__init__(self)
        # Interface: stanza as callback for XML stanza objects
        self._callback = callback
        # Internal stuff
        self._parser = xml.sax.make_parser()
        self._parser.setFeature(xml.sax.handler.feature_namespaces, True)
        self._parser.setContentHandler(self)
        self._current_name = None
        self._current_node = None
        self._stack = []
        self._open = False

    def parse(self, data):
        """
        Add data to the internal SAX parser.
        """
        try:
            return self._parser.feed(data)
        except Exception, e:
            log.exception('SAX parse error')
            self.signals['invalid'].emit()

    def startElementNS(self, (xmlns, name), qname, attrs):
        """
        SAX Callback.
        """
        if not self._open:
            self._open = True
            if (xmlns, name) != ('http://etherx.jabber.org/streams', 'stream'):
                raise RuntimeError('<stream> expected')
            attrsdict = {}
            for ((ns, key), value) in attrs.items():
                attrsdict[key] = value
            return self._callback(name, xmlns, attrsdict)
        callback = self.saxparser.get(name, xmlns)
        if callback is None and self._current_node is None:
            callback = ElementParser
        if callback:
            self._stack.append((self._current_name, self._current_node))
            self._current_node = callback(name, xmlns, attrs)
            self._current_name = (name, xmlns)
            return
        if self._current_node is not None:
            return self._current_node.start_element(name, xmlns, attrs)
        log.error('no parser for %s', name)

    def endElementNS(self, (xmlns, name), qname):
        """
        SAX Callback.
        """
        if (name, xmlns) == self._current_name:
            result = self._current_node.get_result()
            self._current_name, self._current_node = self._stack.pop()
            if self._current_node is None:
                # stanza handling
                return self._callback(name, xmlns, result)
            # element with special parser
            return self._current_node.parsed_element(name, xmlns, result)
        if self._current_node is not None:
            self._current_node.end_element(name, xmlns)

    def characters(self, c):
        """
        SAX callback
        """
        if self._current_node is not None:
            self._current_node.characters(c)
