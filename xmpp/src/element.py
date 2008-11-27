# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# element.py - Simple XML Element
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

__all__ = [ 'Element', 'Message', 'IQ', 'Result', 'Error' ]

import re

# kaa imports
import kaa

class JID(str):
    """
    Class for handling a JID

    Todo: Add stringprep parsing
          This class is not yet used
    """
    _re_jid1 = re.compile('([^@]*)@([^/:]*):?([0-9]+)?/?(.*)')
    _re_jid2 = re.compile('(@)?([^/:]*):?([0-9]+)?/?(.*)')

    def __init__(self, jid):
        """
        Create a JID object from a string.

        :param from_stream: if set to true the jid is created from information
            parsed from a stream. This is important for stringprep handling.
        """
        parsed = self._re_jid1.match(jid)
        if not parsed:
            parsed = self._re_jid2.match(jid)
        self.name, self.host, self.port, self.resource = parsed.groups()
        self.bare = self.host
        if self.name:
            self.bare = '%s@%s' % (self.name, self.host)
        jid = self.bare
        if self.resource:
            jid = '%s/%s' % (self.bare, self.resource)
        super(JID, self).__init__(jid)

    def is_bare(self):
        """
        Return true if the JID is a bare JID
        """
        return not self.resource

    def __xml__(self):
        """
        Convert JID into XML format using stringprep if required
        """
        return self.full


class Element(object):
    """
    A basic XML element that supports __getitem__ and __setitem__ for attribute
    access and has an iterator and helper functions for child nodes.
    """
    def __init__(self, tagname, xmlns=None, xmlcontent=None, **attr):
        self.tagname = tagname
        self.xmlns = xmlns
        self.text = ''
        self._children = []
        self._attr = attr
        if xmlcontent:
            if isinstance(xmlcontent, (list, tuple)):
                self._children = xmlcontent
            elif isinstance(xmlcontent, Element):
                self._children = [ xmlcontent ]
            else:
                self.text = xmlcontent

    def _escape(self, str):
        """
        Escape some characters to entities.
        """
        return str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').\
               replace("\"", "&quot;")

    def __xml__(self):
        """
        Convert the object into XML.
        """
        s = u'<%s' % self.tagname
        if self.xmlns:
            s += ' xmlns="%s"' % self.xmlns
        for key, value in self._attr.items():
            # FIXME: unicode handling for value
            if value is not None:
                s += ' %s="%s"' % (self._escape(key), self._escape(str(value)))
        if not self._children and not self.text:
            return s +'/>'
        s += '>'
        for c in self._children:
            s += c.__xml__()
        # FIXME: content may be CDATA
        return s + self._escape(self.text.strip()) + '</%s>' % self.tagname

    def __str__(self):
        """
        String output for debugging.
        """
        return self.__xml__().encode('latin-1')

    def append(self, node):
        """
        Append a node to the list of children.
        """
        self._children.append(node)

    def add_child(self, tagname, xmlns=None, xmlcontent=None, **attr):
        """
        Append a node to the list of children.
        """
        node = Element(tagname, xmlns, xmlcontent, **attr)
        self._children.append(node)
        return node

    def has_child(self, name):
        """
        Return if the node has at least one child with the given node name.
        """
        return self.get_child(name) is not None

    def get_child(self, name):
        """
        Return the first child with the given name or None.
        """
        for child in self._children:
            if child.tagname == name:
                return child
        return None

    def get_children(self, name=None):
        """
        Return a list of children with the given name.
        """
        if name is None:
            return self._children[:]
        children = []
        for child in self._children:
            if child.tagname == name:
                children.append(child)
        return children

    def __iter__(self):
        """
        Iterate through the children.
        """
        return self._children.__iter__()

    def get(self, item, default=None):
        """
        Get the given attribute value or None if not set.
        """
        return self._attr.get(item, default)

    def __getitem__(self, item):
        """
        Get the given attribute value or raise a KeyError if not set.
        """
        return self._attr[item]

    def __setitem__(self, item, value):
        """
        Set the given attribute to a new value.
        """
        self._attr[item] = value

    def __getattr__(self, attr):
        """
        Magic function to return the attribute or child with the given name.
        """
        result = self._attr.get(attr)
        if result is not None:
            return result
        return self.get_child(attr)

    def __cmp__(self, other):
        if isinstance(other, (str, unicode)):
            return cmp(self.tagname, other)
        return object.__cmp__(self, other)


class Message(Element):
    """
    XMPP <message> stanza.
    """
    def __init__(self, xfrom, xto, tagname, xmlns=None, xmlcontent=None, **attr):
        Element.__init__(self, tagname, xmlns, xmlcontent, **attr)
        self._routing = ''
        if xfrom:
            self._routing += ' from="%s"' % self._escape(xfrom)
        if xto:
            self._routing += ' to="%s"' % self._escape(xto)

    def __xml__(self):
        """
        Convert the object into XML.
        """
        return u'<message%s>%s</message>' % (self._routing, Element.__xml__(self))


class IQ(kaa.InProgress, Message):
    """
    XMPP <iq> stanza used for set and get. The object is also an InProgress
    object waiting for the result.
    """

    # internal unique id counter
    _next_id = 0

    def __init__(self, xtype, xfrom, xto, tagname, xmlns=None, xmlcontent=None, **attr):
        Message.__init__(self, xfrom, xto, tagname, xmlns, xmlcontent, **attr)
        kaa.InProgress.__init__(self)
        IQ._next_id += 1
        self.id = '%s_%s' % (tagname, IQ._next_id)
        self._attributes = ' type="%s" id="%s"' % (xtype, self.id)

    def __xml__(self):
        """
        Convert the object into XML.
        """
        return u'<iq%s%s>%s</iq>' % (self._routing, self._attributes, Element.__xml__(self))


class Result(Element):
    """
    XMPP <iq> stanza used for a result.
    """

    # link to the iq request
    request = None

    def set_request(self, iq):
        """
        Set the request to this object for additional information.
        """
        self.request = iq

    def __xml__(self):
        """
        Convert the object into XML.
        """
        # FIXME: handle special chars (<>&) and CDATA elements
        args = 'type="result"'
        if self.request:
            args += ' id="%s"' % self.request.get('id')
            if self.request.get('to') is not None:
                args += ' from="%s"' % self.request.get('to')
            if self.request.get('from') is not None:
                args += ' to="%s"' % self.request.get('from')
        if self.tagname is None:
            return u'<iq %s/>' % args
        return u'<iq %s>%s</iq>' % (args, Element.__xml__(self))


class Error(Result):
    """
    XMPP <iq> stanza used for am error result.
    """

    def __init__(self, code, type, error=None):
        if not error:
            error = []
        if not isinstance(error, (list, tuple)):
            error = [ error ]
        Result.__init__(self, 'error', code=code, type=type, xmlcontent=error)

    def __xml__(self):
        """
        Convert the object into XML.
        """
        args = 'type="error"'
        request = ''
        if self.request:
            args += ' id="%s"' % self.request.get('id')
            if self.request.get('to') is not None:
                args += ' from="%s"' % self.request.get('to')
            if self.request.get('from') is not None:
                args += ' to="%s"' % self.request.get('from')
            for child in self.request:
                request = child.__xml__()
        return u'<iq %s>%s%s</iq>' % (args, request, Element.__xml__(self))
