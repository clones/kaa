# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# linklocal.py - XEP-0174: link-local messaging
# -----------------------------------------------------------------------------
# $Id$
#
# Extension for link-local communication using multicast DNS for
# service discovery.  To announce a client, the client must call
# 'announce', listening to events is always active.
#
# The Client object must activate the 'link-local' extension. For
# link-local discovered clients the stream will be opened when
# something needs to be send using the RemoteNode object
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

# python imports
import logging

# tls support
import tlslite.api

# kaa imports
import kaa
from kaa.utils import property
import kaa.net.mdns
import kaa.net.tls
import kaa.weakref

# kaa.xmpp imports
from .. import api as xmpp

# get logging object
log = logging.getLogger('xmpp')

NS_TLS = 'urn:ietf:params:xml:ns:xmpp-tls'

class TLSServerFeature(xmpp.Feature):
    """
    STARTTLS feature: Responder part.
    """

    # feature identifier
    identifier = 'starttls', NS_TLS

    def __init__(self, stream, client, credentials):
        """
        Create object and add it to a stream.
        """
        super(TLSServerFeature, self).__init__(stream)
        self.client = kaa.weakref.weakref(client)
        self.credentials = credentials

    @property
    def xmlnode(self):
        """
        Create <feature> node
        """
        return xmpp.Element('starttls', NS_TLS, [ xmpp.Element('required'), self.credentials.handshake_initiator() ])

    @xmpp.stanza(xmlns=NS_TLS, coroutine=True)
    def _handle_starttls(self, starttls):
        """
        <starttls> from the client, initiate TLS
        """
        if starttls.security:
            response = self.credentials.handshake_finalize(starttls.security)
            if not response:
                self.send(xmpp.Element('failure', NS_TLS))
                # FIXME: close stream
                yield None
            self.method = response.method.name
            # send final offer back
            self.send(xmpp.Element('proceed', NS_TLS, content=response))
        else:
            # fallback if XEP-250 is unsupported
            self.method = 'x509'
            self.send(xmpp.Element('proceed', NS_TLS))
        kwargs = {}
        if self.method == 'x509':
            kwargs['key'] = self.credentials.x509_keyinfo
            kwargs['request_cert'] = True
        if self.method == 'srp':
            jid = self.stream.routing.get('from')
            password = self.credentials.srp_get_password(jid)
            if isinstance(password, kaa.InProgress):
                password = yield password
            db = tlslite.api.VerifierDB()
            db[jid] = db.makeVerifier(jid, password, 2048)
            kwargs['srp'] = db
        yield self.stream.starttls(checker=self.check, **kwargs)
        self.finish(None)

    def check(self, connection):
        """
        tlslite checker that accepts all keys and stores the key as
        self.server_cert and self.client_cert in this object.
        """
        if self.method == 'x509':
            cert = connection.session.clientCertChain
            self.stream.properties['peer-certificate'] = cert
            if not self.credentials.x509_check(cert):
                raise kaa.net.tls.TLSAuthenticationError('peer certificate unknown')
        if self.method == 'srp':
            if not connection.session.srpUsername:
                raise kaa.net.tls.TLSAuthenticationError('peer SRP unknown')
        self.stream.properties['secure'] = True


class TLSClientFeature(xmpp.Feature):
    """
    STARTTLS feature: Initiator part.
    """

    # feature identifier
    identifier = 'starttls', NS_TLS

    def __init__(self, stream, client, remote, credentials):
        """
        Create object and add it to a stream.
        """
        super(TLSClientFeature, self).__init__(stream)
        self.client = kaa.weakref.weakref(client)
        self.remote = kaa.weakref.weakref(remote)
        self.credentials = credentials

    def run(self, feature):
        """
        Start the feature
        """
        starttls = xmpp.Element('starttls', NS_TLS)
        if feature.security:
            starttls.append(self.credentials.handshake_responder(feature.security))
        self.send(starttls)
        return self

    @xmpp.stanza(xmlns=NS_TLS, coroutine=True)
    def _handle_proceed(self, proceed):
        """
        Callback from the server to proceed with TLS
        """
        self.method = 'x509'
        if proceed.security:
            self.method = proceed.security.method.name
        kwargs = {}
        if self.method == 'x509':
            kwargs['key'] = self.credentials.x509_keyinfo
        if self.method == 'srp':
            password = self.credentials.srp_get_password(self.remote.jid)
            if isinstance(password, kaa.InProgress):
                password = yield password
            kwargs['srp'] = (self.client.jid, password)
        yield self.stream.starttls(checker=self.check, **kwargs)
        self.finish(None)

    @xmpp.stanza(xmlns=NS_TLS, coroutine=True)
    def _handle_failure(self, failure):
        """
        Callback from the server on TLS failure
        """
        # FIXME: this does not work
        self.throw(IOError, IOError('TLS Failure'), None)

    def check(self, connection):
        """
        tlslite checker that accepts all keys and stores the key as
        self.server_cert and self.client_cert in this object.
        """
        if self.method == 'x509':
            cert = connection.session.serverCertChain
            self.stream.properties['peer-certificate'] = cert
            if not self.credentials.x509_check(cert):
                raise kaa.net.tls.TLSAuthenticationError('peer certificate unknown')
        if self.method == 'srp':
            if not connection.session.srpUsername:
                raise kaa.net.tls.TLSAuthenticationError('peer SRP unknown')
        self.stream.properties['secure'] = True



class XEP0174(xmpp.ClientPlugin):
    """
    Plugin for XEP-0174: Link-local messaging.
    """

    requires = [ 'e2e-streams', 'xtls', 'disco' ]

    # tcp port for incoming connections
    __port = None

    def _extension_activate(self, announce=False):
        """
        Activate the service browser.
        """
        self._streams = {}
        presence = kaa.net.mdns.get_type('_presence._tcp')
        presence.signals['added'].connect(self._mdns_added)
        presence.signals['removed'].connect(self._mdns_removed)
        for s in presence.services:
            self._mdns_added(s)
        if announce:
            self.announce()

    @kaa.timed(0, kaa.OneShotTimer)
    def announce(self):
        """
        Announce presence.
        """
        kaa.net.mdns.provide(
            self.client.appname, '_presence._tcp', self.port, {
              'ver' : self.get_extension('disco').capabilities,
              'jid' : self.client.jid,
              'node': self.client.appname,
        })

    def _mdns_added(self, info):
        """
        Callback from mdns when a new _presence._tcp service is found.
        """
        if self.client.appname == info.name and info.local:
            # found ourself, ignore
            return
        # get a unique name
        name = '%s#%s' % (info.txt.get('node'), info.txt.get('ver'))
        if name in self._streams:
            # already known entity, maybe different interface
            return
        # get jid from txt record
        jid = info.txt.get('jid')
        if not jid:
            log.error('link-local node without jid')
            return
        # create initiator stream and connect to RemoteNode object
        remote = self.client.get_node(jid)
        stream = remote.get_extension('e2e-streams').create_stream((info.address, info.port))
        credentials = self.client.get_extension('xtls').credentials(self.client)
        # we need to save the feature somewhere for the reference counter/gc
        stream._feature_tls = TLSClientFeature(stream, self.client, remote, credentials)
        # FIXME: bad code
        remote.stream = stream
        # store and emit signal
        self._streams[name] = remote
        self.client.signals['presence'].emit(remote)

    def _mdns_removed(self, info):
        """
        Callback from mdns when a service is gone.
        """
        node = '%s#%s' % (info.txt.get('node'), info.txt.get('ver'))
        if node in self._streams:
            remote = self._streams.pop(node)
            # FIXME: update remote to reflect new status
            self.client.signals['presence'].emit(remote)

    @property
    def port(self):
        """
        Return client to client communication port.
        """
        if self.__port is None:
            self.__port = kaa.net.tls.TLSSocket()
            self.__port.signals['new-client'].connect(self._new_connection)
            self.__port.listen(0)
        return self.__port.address[1]

    @kaa.coroutine()
    def _new_connection(self, socket):
        """
        New connection on the socket.
        """
        stream = self.get_extension('e2e-streams').create_stream(socket, None)
        # connect server features
        tls = TLSServerFeature(stream, self.client, self.get_extension('xtls').credentials(self.client))
        # wait for connect
        if (yield stream.signals.subset('connected', 'closed').any())[0]:
            # closed before connected
            log.error('error during e2e-streams connect to %s', stream.routing.get('from'))
            yield None
        if not stream.routing.get('from'):
            log.error('no "from" provided in <stream>')
            stream.close()
            yield None
        # override stream object
        self.client.get_node(stream.routing.get('from')).stream = stream
        yield stream


# register extension plugin
xmpp.add_extension('link-local', None, XEP0174, None)
