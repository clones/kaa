# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# client.py - XMPP client
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

__all__ = [ 'Client' ]

# python imports
import re
import os
import logging

# kaa imports
import kaa
from kaa.utils import property

# kaa.xmpp imports
import feature
import plugin
from remote import RemoteNode
from stream import XMPPStream
from element import Message, IQ
from error import XMPPConnectError
from db import Database

# get logging object
log = logging.getLogger('xmpp')

class RemoteNodes(dict):
    def __init__(self, client):
        self._client = client

    def get(self, jid, create=True):
        """
        Get RemoteNode object for the given jid.
        """
        remote = super(RemoteNodes, self).get(jid)
        if create and remote is None:
            remote = RemoteNode(self._client, self._client.cache.get_node(jid))
        self[jid] = remote
        return remote

    def remove(self, jid):
        """
        Remove a RemoteNode object from the internal list.
        @bug: this should be done by the garbage collector or from presence information
        """
        self.pop(jid).shutdown()


class Client(object):
    """
    Class for an XMPP client.
    """

    _re_jid = re.compile('([^@]*)@([^/:]*):?([0-9]+)?/?(.*)')

    def __init__(self, application, jid):
        self.stream = XMPPStream()
        self.signals = kaa.Signals('connected', 'message', 'presence')
        self.stream.signals['message'].connect(self.signals['message'].emit)
        self.remote_nodes = RemoteNodes(self)
        self.appname = application
        self.jid = jid
        self.cache = Database(application)
        # features for XEP-0030
        self.features = []
        # extension callbacks
        self._plugins = {}
        # add plugins
        plugin.enhance_client(self)

    @kaa.coroutine()
    def connect(self, password):
        """
        Connect to the XMPP server.
        """
        if not self.jid:
            raise AttributeError('no jid provided')
        name, host, port, resource = self._re_jid.match(self.jid).groups()
        if not port:
            port = 5222
        # connect some basic features
        tls = feature.TLS(self.stream)
        sasl = feature.SASL(self.stream)
        sasl.username = name
        sasl.password = password
        bind = feature.Bind(self.stream)
        bind.resource = resource
        # connect to server
        session = feature.Session(self.stream)
        self.stream.connect((host, port))
        sig = self.stream.signals
        if (yield self.stream.signals.subset('connected', 'closed').any())[0]:
            # closed before connected
            raise XMPPConnectError('stream closed by peer')
        self.jid = bind.jid
        self.signals['connected'].emit()

    def xmpp_connect(self, obj):
        """
        Connect XMPP callbacks in the given object.
        """
        self.stream.xmpp_connect(obj)

    def xmpp_disconnect(self, obj):
        """
        Disconnect XMPP callbacks in the given object.
        """
        self.stream.xmpp_disconnect(obj)

    def send_stanza(self, stanza):
        """
        Send a raw stanza
        """
        return self.stream.send(stanza)

    def message(self, tagname, xmlns=None, content=None, **attr):
        """
        Send a message stanza
        """
        to = attr.pop('to', None)
        m = Message(self.jid, to, tagname, xmlns, content, **attr)
        self.send_stanza(m)

    def iqset(self, tagname, xmlns=None, content=None, **attr):
        """
        Send an <iq> set stanza
        """
        to = attr.pop('to', None)
        i = IQ('set', self.jid, to, tagname, xmlns, content, **attr)
        self.send_stanza(i)
        return i

    def iqget(self, tagname, xmlns=None, content=None, **attr):
        """
        Send an <iq> get stanza
        """
        to = attr.pop('to', None)
        i = IQ('get', self.jid, to, tagname, xmlns, content, **attr)
        self.send_stanza(i)
        return i

    def get_node(self, jid, create=True):
        """
        Get RemoteNode object for the given jid.

        :param jid: RemoteNode jid
        :param create: create RemoteNode object if is does not exist
        """
        return self.remote_nodes.get(jid, create)

    def activate_extension(self, ext, *args, **kwargs):
        """
        Activate the given plugin
        """
        if hasattr(self, ext):
            # auto connected extensions
            return getattr(self, ext)
        if not ext in self._plugins:
            # Add extension plugin to the client.
            disco, cls = plugin.get_plugin(ext)[:2]
            obj = cls()
            obj._xmpp_disco = disco
            obj._extension_connect(self)
            obj._extension_activate(*args, **kwargs)
            self._plugins[ext] = obj
        for feature in self._plugins[ext]._xmpp_disco:
            if feature and not feature in self.features:
                self.features.append(feature)
        return self._plugins[ext]

    def get_extension(self, ext):
        """
        Return the plugin for the given extension.
        """
        return self._plugins.get(ext)

    @property
    def extensions(self):
        """
        Get all supported extensions
        """
        return self._plugins.keys()
