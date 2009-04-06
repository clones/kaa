# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# e2e_streams.py -
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.xmpp - XMPP framework for the Kaa Media Repository
# Copyright (C) 2008-2009 Dirk Meyer
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

__all__ = [ 'E2EStream', 'Initiator', 'Responder' ]

# python imports
import logging

# kaa imports
import kaa

# kaa.xmpp imports
from .. import api as xmpp

# get logging object
log = logging.getLogger('xmpp')


class E2EStream(xmpp.stream.XMPPStream):
    """
    XMPPStream from End-to-End communication.
    """
    def __init__(self, client, remote):
        """
        Create End-to-End stream.
        """
        super(E2EStream, self).__init__()
        self._client_callbacks = client.stream._client_callbacks
        self.properties['e2e-stream'] = True
        self.signals['message'] = client.stream.signals['message']
        self.routing = { 'to': client.jid }
        if remote:
            self.routing['from'] = remote.jid
        self._queue = []

    def send(self, data, feature_negotiation=False):
        """
        Send a stanza to the remote node. The E2EStream removes all routing
        information and may queue stanzas while connecting.
        """
        if isinstance(data, xmpp.Message):
            data._routing = ''
        if feature_negotiation or self.status == xmpp.stream.XMPPStream.CONNECTED:
            return super(E2EStream, self).send(data, feature_negotiation)
        return self._queue.append(data)

    def _handle_stanza(self, name, xmlns, stanza):
        """
        Generic stream stanza callback. The E2EStream needs to add the routing
        informations back for the handler. Existing routing informations will
        be overwritten.
        """
        if isinstance(stanza, xmpp.Element) and self.status == xmpp.stream.XMPPStream.CONNECTED:
            # override from and to
            stanza._attr['from'] = self.routing['from']
            stanza._attr['to'] = self.routing['to']
        super(E2EStream,self)._handle_stanza(name, xmlns, stanza)

    def _connected(self):
        """
        Callback when stream is connected.
        """
        super(E2EStream, self)._connected()
        while self._queue:
            self.send(self._queue.pop(0))



class Initiator(xmpp.RemotePlugin):
    """
    Initiator plugin (RemoteNode)
    """
    class Stream(E2EStream):
        """
        XMPPStream between client and client: Initiator part.
        Similar to a client for normal client to server stream.
        """
        def __init__(self, addr, client, remote):
            """
            Create the stream object

            :param addr: ip address or socket object
            :param client: client object
            :param remote: remote node object
            """
            super(Initiator.Stream, self).__init__(client, remote)
            self._addr = addr
            self._greeting = '''<?xml version="1.0"?>
            <stream:stream from="%s" to="%s" xmlns="jabber:client"
               xmlns:stream="http://etherx.jabber.org/streams"
               version="1.0">''' % (client.jid, remote.jid)

        def send(self, data, feature_negotiation=False):
            """
            Send a stanza to the remote node. Auto-connect if needed.
            """
            if self.status == xmpp.stream.XMPPStream.NOT_CONNECTED:
                self.connect()
            super(Initiator.Stream, self).send(data, feature_negotiation)

        def connect(self):
            """
            Connect to the given host/port address
            """
            if self.status != xmpp.stream.XMPPStream.NOT_CONNECTED:
                # already connected or trying to
                return
            if isinstance(self._addr, kaa.Socket):
                self.status = self.CONNECTING
                # address is a socket
                self._socket = self._addr
                self._addr = None
                self.restart()
                return
            return super(Initiator.Stream, self).connect(self._addr)


    def create_stream(self, address):
        """
        Connect to address and open a stream.

        :param address: IP address or socket object
        """
        return Initiator.Stream(address, self.client, self.remote)



class Responder(xmpp.ClientPlugin):
    """
    Initiator plugin (Client object)
    """

    class Stream(E2EStream):
        """
        XMPPStream between client and client: Responder part.
        Similar to a server for normal client to server stream.
        """
        def __init__(self, socket, client, remote):
            super(Responder.Stream, self).__init__(client, remote)
            self._socket = socket
            self._featurelist = []
            self.restart()

        @xmpp.stanza(xmlns=xmpp.stream.NS_STREAM)
        def _handle_stream(self, attributes):
            """
            Handle new <stream> element.

            :param attributes: the XML attributes of the <stream> open tag
            """
            if not self.routing.get('from'):
                self.routing['from'] = attributes.get('from')
            # send <stream> element
            self._socket.write('''<?xml version="1.0"?>
            <stream:stream from="%s" id="%s" xmlns="jabber:client"
                xmlns:stream="http://etherx.jabber.org/streams"
                version="1.0">''' % (attributes.get('to'), "streamid"))
            # send features
            features = xmpp.Element('stream:features')
            for f in self._featurelist:
                if not f.finished:
                    features.append(f.xmlnode)
            self._socket.write(unicode(features))
            # FIXME: bad hack:
            if not features.get_children():
                # remove feature callbacks
                # FIXME: check memory leak when setup fails
                for feature in self._featurelist:
                    self.xmpp_disconnect(feature, private=True)
                self._connected()

        def add_feature(self, feature):
            """
            Add a feature to the stream.

            :param feature: feature object
            """
            self.xmpp_connect(feature, private=True)
            self._featurelist.append(feature)

        @kaa.coroutine()
        def starttls(self, session=None, key=None, request_cert=False, srp=None, checker=None):
            """
            Start TLS on the socket.
            """
            try:
                yield self._socket.starttls_server(session, key, request_cert, srp, checker)
            except Exception, e:
                log.exception('tls error')
                self.close(stream_close=False)
                yield False
            self.restart()


    def create_stream(self, socket, remote):
        return Responder.Stream(socket, self.client, remote)


# register extension
xmpp.add_extension('e2e-streams', None, Responder, Initiator)
