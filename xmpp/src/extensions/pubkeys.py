# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# pubkey.py - XEP-0189: Public Key Publishing
# -----------------------------------------------------------------------------
# $Id$
#
# Status: Not working
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
import hashlib

# kaa imports
import kaa
from kaa.utils import property
# FIXME: TLS support
from kaa.net.tls.tlslite import tlsapi

# kaa.xmpp imports
from .. import api as xmpp

# get logging object
log = logging.getLogger('xmpp')

NS_PUBKEY = 'urn:xmpp:tmp:pubkey'

class X509(object, tlsapi.X509):

    @property
    def base64(self):
        return tlslite.utils.cryptomath.bytesToBase64(self.writeBytes())

    @base64.setter
    def base64(self, data):
        self.parseBinary(tlslite.utils.cryptomath.base64ToBytes(data))

    @property
    def data(self):
        return self.writeBytes()

    @property
    def fingerprint(self):
        return hashlib.sha1(self.writeBytes()).hexdigest()

    @property
    def chain(self):
        return tlsapi.X509CertChain([self])

class KeyInfo(object):

    __x509 = None
    __private = None

    def __init__(self):
        self.signatures = []

    @property
    def certificate(self):
        if not self.__x509:
            self.__x509 = X509()
        return self.__x509

    @property
    def private(self):
        return self.__private

    @property
    def fingerprint(self):
        if not self.__x509:
            return None
        return self.__x509.fingerprint

    def sign(self, data):
        return tlslite.utils.cryptomath.bytesToBase64(self.__private.hashAndSign(data))

    def verify(self, signature, data):
        signature = tlslite.utils.cryptomath.base64ToBytes(signature)
        return self.__x509.publicKey.hashAndVerify(signature, data)

    def add_signature(self, issuer, signature):
        self.signatures.append((issuer, signature))

    def load_pemfile(self, fname):
        pem = open(fname).read()
        self.__private = tlsapi.parsePEMKey(pem, private=True)
        self.__x509 = X509()
        self.__x509.parse(pem)

    def __xml__(self):
        e = xmpp.Element('keyinfo', 'urn:xmpp:tmp:pubkey')
        e.add_child('name', content=self.fingerprint)
        e.add_child('x509cert', content=self.certificate.base64)
        for issuer, signature in self.signatures:
            s = e.add_child('signature')
            s.add_child('issuer', content=issuer)
            s.add_child('value', method='RSA-SHA1', content=signature)
        return e

    def __parsexml__(self, e):
        self.certificate.base64 = e.x509cert.content
        if self.fingerprint != e.name.content:
            raise AttributeError
        for s in e.get_children('signature'):
            self.add_signature(s.issuer.content, s.value.content)
