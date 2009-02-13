# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# feature.py - Some XMPP features pre-defined by kaa.xmpp
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

__all__ = [ 'TLS', 'SASL', 'Bind', 'Session' ]

# python imports
import base64

# kaa imports
import kaa
from kaa.utils import property
from kaa.weakref import weakref

# kaa.xmpp imports
from element import Element, IQ
import parser as xmpp

# namespaces
NS_TLS = 'urn:ietf:params:xml:ns:xmpp-tls'
NS_SASL = 'urn:ietf:params:xml:ns:xmpp-sasl'
NS_BIND = 'urn:ietf:params:xml:ns:xmpp-bind'
NS_SESSION = 'urn:ietf:params:xml:ns:xmpp-session'

class Feature(kaa.InProgress):
    """
    Generic feature base class.
    """

    def __init__(self, stream):
        """
        Create object and add it to a stream.
        """
        super(Feature, self).__init__()
        self.stream = weakref(stream)
        stream.add_feature(self)

    def send(self, data):
        """
        Send data to the stream (if connected).
        """
        self.stream.send(data, feature_negotiation=True)
        return data


class TLS(Feature):
    """
    TLS feature for a secure connection.
    @todo: handle TLS errors, check remote certificate
    """

    identifier = 'starttls', NS_TLS

    def run(self, tls):
        """
        Start the feature.
        """
        self.send(Element('starttls', NS_TLS))
        return self

    @xmpp.stanza(xmlns=NS_TLS)
    def _handle_proceed(self, proceed):
        """
        Callback from the server to proceed with TLS (starttls).

        @todo: add checker for server certificate
        """
        self.waitfor(self.stream.starttls())


class SASL(Feature):
    """
    SASL feature for authentication.
    """

    identifier = 'mechanisms', NS_SASL

    class SASLError(Exception):
        """
        Exception raised if SASL failed.
        """
        pass

    def run(self, mechanisms):
        """
        Start the feature.
        """
        # FIXME: support MD5 and check if PLAIN is allowed
        text = base64.b64encode('\x00%s\x00%s' % (self.username, self.password))
        self.send(Element('auth', NS_SASL, text, mechanism='PLAIN'))
        return self

    @xmpp.stanza(xmlns=NS_SASL)
    def _handle_success(self, result):
        """
        Callback on successfull SASL negotiation.
        """
        self.stream.restart()
        self.finish(True)

    @xmpp.stanza(xmlns=NS_SASL)
    def _handle_failure(self, result):
        """
        Callback on failed SASL negotiation.
        """
        self.throw(SASL.SASLError, result, None)


class Bind(Feature):
    """
    Bind feature to bind a resource on the server
    """

    identifier = 'bind', NS_BIND
    resource = None

    @kaa.coroutine()
    def run(self, stanza):
        """
        Start the feature.
        """
        iq = IQ('set', None, None, 'bind', NS_BIND)
        if self.resource:
            iq.add_child('resource', content=self.resource)
        result = yield self.send(iq)
        self.jid = result.get_child('jid').content
        self.finish(True)


class Session(Feature):
    """
    Session feature to open a new session.
    """

    identifier = 'session', NS_SESSION

    def run(self, stanza):
        """
        Start the feature.
        """
        return self.send(IQ('set', None, None, 'session', NS_SESSION))
