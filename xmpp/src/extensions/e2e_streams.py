# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# e2e_streams.py - XEP-0246: End-to-End XML Streams
#                  XEP-0250: C2C Authentication Using TLS
# -----------------------------------------------------------------------------
# $Id$
#
# This module implements XEP-0246 (End-to-End XML Streams) and
# optional an authentication mechanism defined by XEP-0250 (C2C
# Authentication Using TLS)
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

__all__ = [ 'E2EStream', 'Initiator', 'Responder' ]

# python imports
import os
import logging

# tls support
import tlslite.api

# kaa imports
import kaa
from kaa.utils import property
import kaa.weakref
import kaa.net.tls

# kaa.xmpp imports
from .. import api as xmpp
from pubkeys import KeyInfo, NS_PUBKEY

# get logging object
log = logging.getLogger('xmpp')

# namespaces
NS_TLS = 'urn:ietf:params:xml:ns:xmpp-tls'
NS_C2CTLS ='urn:xmpp:tmp:c2ctls'

class Credentials(object):
    """
    Credentials for TLS authentication. As a default X.509
    certificates from known_clients are read and openssl is used to
    create a client certificate.
    """
    def __init__(self, client):
        self.client = client
        self.x509_init()

    def x509_init(self):
        """
        Set of X.509 certificate and read known_clients file.
        """
        pemfile = os.path.join(xmpp.config.cachedir, self.client.appname + '.pem')
        if not os.path.isfile(pemfile):
            # FIXME: hide output and check for openssl
            os.system("openssl req -subj '/CN=%s' -x509 -nodes -days 365 -newkey "\
                "rsa:1024 -keyout %s -out %s" % (self.client.appname, pemfile, pemfile))
        self.x509_keyinfo = KeyInfo()
        self.x509_keyinfo.load_pemfile(pemfile)
        self.known_clients_x509 = []
        known = os.path.join(xmpp.config.cachedir, 'known_clients')
        if os.path.isfile(known):
            for line in open(known).readlines():
                key = KeyInfo()
                key.certificate.base64 = line.split(' ')[1]
                self.known_clients_x509.append(key.certificate)

    def x509_supported(self):
        """
        Return if X.509 certificates are supported. Default is true.
        """
        return True

    def x509_check(self, certificate):
        """
        Check the remote certificate. The deafult behaviour is only to
        allow known clients. If the certificate is ok, return True.
        """
        return certificate.validate(self.known_clients_x509)

    def x509_offer(self):
        """
        Return XEP-250 offer for X.509
        """
        return xmpp.Element('keyinfo', NS_PUBKEY, xmpp.Element('name', content=self.x509_keyinfo.fingerprint))

    def x509_offer_check(self, keyinfo):
        """
        Check if the XEP-250 offer for X.509 contains a known certificate
        """
        fingerprint = keyinfo.get_child('name').content
        for known in self.known_clients_x509:
            if fingerprint == known.fingerprint:
                return True
        return False

    def srp_supported(self):
        """
        Return if SRP is supported
        """
        return False

    def srp_get_password(self, remote):
        """
        Function to return the SRP password. This can be a coroutine if needed.
        The function must be implemented by an inherting class and srp_supported()
        should return True in that case.
        """
        raise NotImplementedError

    def srp_offer(self):
        """
        Return XEP-250 offer for SRP
        """
        return xmpp.Element('srp', NS_C2CTLS)

    @classmethod
    def install(cls):
        Responder.credentials = cls



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
        def __init__(self, addr, client, remote, credentials):
            """
            Create the stream object

            :param addr: ip address or socket object
            :param client: client object
            :param remote: remote node object
            """
            super(Initiator.Stream, self).__init__(client, remote)
            self._addr = addr
            self._feature_tls = Initiator.TLSFeature(self, client, remote, credentials)
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


    class TLSFeature(xmpp.Feature):
        """
        STARTTLS feature: Initiator part.
        """

        # feature identifier
        identifier = 'starttls', NS_TLS

        def __init__(self, stream, client, remote, credentials):
            """
            Create object and add it to a stream.
            """
            super(Initiator.TLSFeature, self).__init__(stream)
            self.client = kaa.weakref.weakref(client)
            self.remote = kaa.weakref.weakref(remote)
            self.credentials = credentials or Credentials(client)

        def run(self, feature):
            """
            Start the feature
            """
            starttls = xmpp.Element('starttls', NS_TLS)
            offer = feature.get_child('offer')
            if offer:
                answer = xmpp.Element('offer', NS_C2CTLS)
                for keyinfo in offer.get_children('keyinfo'):
                    if self.credentials.x509_offer_check(keyinfo) and self.credentials.x509_supported():
                        answer.append(self.credentials.x509_offer())
                if self.credentials.srp_supported() and offer.get_child('srp'):
                    answer.append(self.credentials.srp_offer())
                starttls.append(answer)
            self.send(starttls)
            return self

        @xmpp.stanza(xmlns=NS_TLS, coroutine=True)
        def _handle_proceed(self, proceed):
            """
            Callback from the server to proceed with TLS
            """
            self.method = 'x509'
            if proceed.get_child('offer') and proceed.get_child('offer').get_child('srp'):
                self.method = 'srp'
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


    def create_stream(self, address):
        """
        Connect to address and open a stream.

        :param address: IP address or socket object
        """
        credentials = self.client.get_extension('e2e-streams').credentials(self.client)
        return Initiator.Stream(address, self.client, self.remote, credentials)



class Responder(xmpp.ClientPlugin):
    """
    Initiator plugin (Client object)
    """
    # tcp port for incoming connections
    __port = None

    # callback to create Credentials object
    credentials = Credentials

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
        def starttls(self, session=None, key=None, request_cert=False, srp=None,
                     checker=None):
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


    class TLSFeature(xmpp.Feature):
        """
        STARTTLS feature: Responder part.
        """

        # feature identifier
        identifier = 'starttls', NS_TLS

        def __init__(self, stream, client, remote, credentials):
            """
            Create object and add it to a stream.
            """
            super(Responder.TLSFeature, self).__init__(stream)
            self.client = kaa.weakref.weakref(client)
            self.remote = kaa.weakref.weakref(remote)
            self.credentials = credentials or Credentials(client)

        @property
        def xmlnode(self):
            """
            Create <feature> node
            """
            offer = xmpp.Element('offer', NS_C2CTLS)
            if self.credentials.x509_supported():
                offer.append(self.credentials.x509_offer())
            if self.credentials.srp_supported():
                offer.append(self.credentials.srp_offer())
            return xmpp.Element('starttls', NS_TLS, [ xmpp.Element('required'), offer ])

        @xmpp.stanza(xmlns=NS_TLS, coroutine=True)
        def _handle_starttls(self, starttls):
            """
            <starttls> from the client, initiate tls
            """
            offer = starttls.get_child('offer')
            if offer:
                for keyinfo in offer.get_children('keyinfo'):
                    if self.credentials.x509_offer_check(keyinfo) and self.credentials.x509_supported():
                        # great, let us use X.509
                        self.method = 'x509'
                        break
                else:
                    # X.509 failed, maybe SRP works
                    if self.credentials.srp_supported() and offer.get_child('srp'):
                        # ok, let us use SRP
                        self.method = 'srp'
                    else:
                        # Oops, no method left, stop
                        self.send(xmpp.Element('failure', NS_TLS))
                        # FIXME: close stream
                        yield None
            else:
                # fallback if XEP-250 is unsupported
                self.method = 'x509'
            # send final offer back
            offer = xmpp.Element('offer', NS_C2CTLS)
            kwargs = {}
            if self.method == 'x509':
                kwargs['key'] = self.credentials.x509_keyinfo
                kwargs['request_cert'] = True
                # final offer is X.509
                offer.append(self.credentials.x509_offer())
            if self.method == 'srp':
                if self.remote: jid = self.remote.jid
                else: jid = self.stream.routing.get('from')
                password = self.credentials.srp_get_password(jid)
                if isinstance(password, kaa.InProgress):
                    password = yield password
                db = tlslite.api.VerifierDB()
                db[jid] = db.makeVerifier(jid, password, 2048)
                kwargs['srp'] = db
                # final offer is SRP
                offer.append(self.credentials.srp_offer())
            self.send(xmpp.Element('proceed', NS_TLS, offer))
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


    @kaa.coroutine()
    def new_connection(self, socket, remote=None):
        """
        New connection on the socket.

        :param socket: socket for communication
        :param remote: remote object (if known)
        """
        stream = Responder.Stream(socket, self.client, remote)
        # connect server features
        tls = Responder.TLSFeature(stream, self.client, remote, self.credentials(self.client))
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

    @property
    def port(self):
        """
        Return client to client communication port.
        """
        if self.__port is None:
            self.__port = kaa.net.tls.TLSSocket()
            self.__port.signals['new-client'].connect(self.new_connection)
            self.__port.listen(0)
        return self.__port.address[1]


# register extension
xmpp.add_extension('e2e-streams', NS_C2CTLS, Responder, Initiator)
