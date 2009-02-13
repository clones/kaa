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
import xml.sax.saxutils

# kaa imports
import kaa
from kaa.saxutils import Element

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


class Message(Element):
    """
    XMPP <message> stanza.
    """
    def __init__(self, xfrom, xto, tagname, xmlns=None, content=None, **attr):
        Element.__init__(self, tagname, xmlns, content, **attr)
        self._routing = ''
        if xfrom:
            self._routing += ' from=%s' % xml.sax.saxutils.quoteattr(xfrom)
        if xto:
            self._routing += ' to=%s' % xml.sax.saxutils.quoteattr(xto)

    def __unicode__(self):
        """
        Convert the element into an XML unicode string.
        """
        return u'<message%s>%s</message>' % (self._routing, Element.__unicode__(self))


class IQ(kaa.InProgress, Message):
    """
    XMPP <iq> stanza used for set and get. The object is also an InProgress
    object waiting for the result.
    """

    # internal unique id counter
    _next_id = 0

    def __init__(self, xtype, xfrom, xto, tagname, xmlns=None, content=None, **attr):
        Message.__init__(self, xfrom, xto, tagname, xmlns, content, **attr)
        kaa.InProgress.__init__(self)
        IQ._next_id += 1
        self.id = '%s_%s' % (tagname, IQ._next_id)
        self._attributes = ' type="%s" id="%s"' % (xtype, self.id)

    def __unicode__(self):
        """
        Convert the element into an XML unicode string.
        """
        return u'<iq%s%s>%s</iq>' % (self._routing, self._attributes, Element.__unicode__(self))


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

    def __unicode__(self):
        """
        Convert the element into an XML unicode string.
        """
        args = 'type="result"'
        if self.request:
            args += ' id="%s"' % self.request.get('id')
            if self.request.get('to') is not None:
                args += ' from="%s"' % self.request.get('to')
            if self.request.get('from') is not None:
                args += ' to="%s"' % self.request.get('from')
        if self.tagname is None:
            return u'<iq %s/>' % args
        return u'<iq %s>%s</iq>' % (args, Element.__unicode__(self))


class Error(Result):
    """
    XMPP <iq> stanza used for am error result.
    """

    def __init__(self, code, type, error=None):
        if not error:
            error = []
        if not isinstance(error, (list, tuple)):
            error = [ error ]
        Result.__init__(self, 'error', code=code, type=type, content=error)

    def __unicode__(self):
        """
        Convert the element into an XML unicode string.
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
                request = unicode(child)
        return u'<iq %s>%s%s</iq>' % (args, request, Element.__unicode__(self))
