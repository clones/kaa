__all__ = [ 'XTLS' ]

# python imports
import os
import logging

# tls support
import tlslite.api

# kaa imports
import kaa
import kaa.net.tls
from .. import api as xmpp
from pubkeys import KeyInfo

# get logging object
log = logging.getLogger('xmpp')

#: Namespaces for In-Band Bytestreams
NS_XTLS = 'urn:xmpp:jingle:security:xtls:0'


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
        Check the remote certificate. The default behaviour is only to
        allow known clients. If the certificate is ok, return True.
        """
        return certificate.validate(self.known_clients_x509)

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

    def handshake_initiator(self):
        """
        Handshake part 1: initiator offer
        """
        security = xmpp.Element('security', NS_XTLS)
        if self.x509_supported():
            security.add_child('fingerprint', algo='sha1', content=self.x509_keyinfo.fingerprint)
            security.add_child('method', name='x509')
        if self.srp_supported():
            security.add_child('method', name='srp')
        return security

    def handshake_responder(self, offer):
        """
        Handshake part 2: responder offer
        """
        security = xmpp.Element('security', NS_XTLS)
        for method in offer.get_children('method'):
            if method.name == 'x509' and self.x509_supported() and offer.fingerprint:
                fingerprint = offer.fingerprint.content
                for known in self.known_clients_x509:
                    if fingerprint == known.fingerprint:
                        security.add_child('fingerprint', algo='sha1', content=self.x509_keyinfo.fingerprint)
                        security.add_child('method', name='x509')
                        break
            if method.name == 'srp' and self.srp_supported():
                security.add_child('method', name='srp')
        return security

    def handshake_finalize(self, offer):
        """
        Handshake part 3: initiator final methods
        """
        security = xmpp.Element('security', NS_XTLS)
        for m in offer.get_children('method'):
            if m.name == 'x509' and self.x509_supported() and offer.fingerprint:
                fingerprint = offer.fingerprint.content
                for known in self.known_clients_x509:
                    if fingerprint == known.fingerprint:
                        security.add_child('method', name='x509')
                        return security
        for m in offer.get_children('method'):
            if m.name == 'srp' and self.srp_supported():
                security.add_child('method', name='srp')
                return security
        return None

    @classmethod
    def install(cls):
        Client.credentials = cls


class XTLS(xmpp.RemotePlugin):

    def _extension_connect(self, remote):
        super(XTLS, self)._extension_connect(remote)
        self.credentials = self.client.get_extension('xtls').credentials(self.client)

    def jingle_initiate(self, session):
        """
        Create transport for Jingle session-initiate
        """
        session.xtls_method = None
        session.xtls_transport = False
        return self.credentials.handshake_initiator()

    def jingle_accept(self, session, initiate):
        """
        Create transport for Jingle session-accept
        """
        session.xtls_method = None
        session.xtls_transport = False
        return self.credentials.handshake_responder(initiate)

    def jingle_security_info(self, session, element):
        """
        """
        if session.initiator == self.client.jid:
            response = self.credentials.handshake_finalize(element)
            if not response:
                raise RuntimeError('no security method')
            session.xtls_method = response.method.name
            session.security_info(response)
        else:
            session.xtls_method = element.method.name
        if session.xtls_transport:
            self.starttls(session)

    def jingle_transport_ready(self, session):
        session.xtls_transport = True
        if session.xtls_method:
            self.starttls(session)

    @kaa.coroutine()
    def starttls(self, session):
        kwargs = {'checker': kaa.Callback(self.tls_checker, session) }
        if session.initiator == self.client.jid:
            if session.xtls_method == 'x509':
                kwargs['key'] = self.credentials.x509_keyinfo
            else:
                password = self.credentials.srp_get_password(session.initiator)
                if isinstance(password, kaa.InProgress):
                    password = yield password
                kwargs['srp'] = (session.initiator, password)
            yield session.socket.starttls_client(**kwargs)
        else:
            if session.xtls_method == 'x509':
                kwargs['key'] = self.credentials.x509_keyinfo
                kwargs['request_cert'] = True
            else:
                password = self.credentials.srp_get_password(session.initiator)
                if isinstance(password, kaa.InProgress):
                    password = yield password
                db = tlslite.api.VerifierDB()
                db[session.initiator] = db.makeVerifier(session.initiator, password, 2048)
                kwargs['srp'] = db
            yield session.socket.starttls_server(**kwargs)
        session.security_ready()

    def tls_checker(self, connection, session):
        if session.initiator == self.client.jid:
            session.cert = connection.session.serverCertChain
        else:
            session.cert = connection.session.clientCertChain
        if session.xtls_method == 'x509':
            if not self.credentials.x509_check(session.cert):
                raise kaa.net.tls.TLSAuthenticationError('peer certificate unknown')
        elif session.xtls_method == 'srp':
            if not connection.session.srpUsername:
                raise kaa.net.tls.TLSAuthenticationError('peer SRP unknown')
        else:
            raise kaa.net.tls.TLSAuthenticationError('unknown method')


class Client(xmpp.ClientPlugin):

    # callback to create Credentials object
    credentials = Credentials

xmpp.add_extension('xtls', NS_XTLS, Client, XTLS)
