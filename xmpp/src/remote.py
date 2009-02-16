# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# remote.py - RemoteNode handling
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
RemoteNode handling
"""

__all__ = [ 'RemoteNode' ]

# python imports
import logging

# kaa imports
import kaa
from kaa.utils import property

# kaa.xmpp imports
import plugin
from element import Message, IQ

# get logging object
log = logging.getLogger('xmpp')

class RemoteNode(object):
    """
    Class to represent a communication peer of a Client.
    """
    def __init__(self, client, cache):
        """
        Create RemoteNode object.
        """
        # Attributes to use outside kaa.xmpp
        self.jid = cache.jid
        self.cache = cache
        self.client = client
        self.stream = client.stream
        # extension API based on features
        self._plugins = {}
        # add plugins
        plugin.enhance_remote_node(self)

    def xmpp_connect(self, obj):
        """
        Connect XMPP callbacks in the given object.

        :param obj: object with functions decorated with the stanza, message or iq decorator
        """
        self.stream.xmpp_connect(obj, jid=self.jid)

    def xmpp_disconnect(self, obj):
        """
        Disconnect XMPP callbacks in the given object.

        :param obj: object with functions decorated with the stanza, message or iq decorator
        """
        self.stream.xmpp_disconnect(obj, jid=self.jid)

    def send_stanza(self, stanza, stream=None):
        """
        Send a stanza

        :param stanza: XML stanza to send
        :param stream: if given use the XML stream instead of the default one
        """
        if stream is None:
            return self.stream.send(stanza)
        return stream.send(stanza)

    def message(self, tagname, xmlns=None, content=None, **attr):
        """
        Send a message stanza

        :param tagname: tag name of the element inside the message stanza
        :param xmlns: namespace of the tag
        :param content: content or children of the node
        :param attr: XML attributes for the node. The additional argument xmppstream can be used to select a stream
        """
        stream = attr.pop('xmppstream', None)
        m = Message(self.client.jid, self.jid, tagname, xmlns, content, **attr)
        self.send_stanza(m, stream)

    def iqset(self, tagname, xmlns=None, content=None, **attr):
        """
        Send an <iq> set stanza

        :param tagname: tag name of the element inside the iq stanza
        :param xmlns: namespace of the tag
        :param content: content or children of the node
        :param attr: XML attributes for the node. The additional argument xmppstream can be used to select a stream
        """
        stream = attr.pop('xmppstream', None)
        i = IQ('set', self.client.jid, self.jid, tagname, xmlns, content, **attr)
        self.send_stanza(i, stream)
        return i

    def iqget(self, tagname, xmlns=None, content=None, **attr):
        """
        Send an <iq> get stanza

        :param tagname: tag name of the element inside the iq stanza
        :param xmlns: namespace of the tag
        :param content: content or children of the node
        :param attr: XML attributes for the node. The additional argument xmppstream can be used to select a stream
        """
        stream = attr.pop('xmppstream', None)
        i = IQ('get', self.client.jid, self.jid, tagname, xmlns, content, **attr)
        self.send_stanza(i, stream)
        return i

    def get_extension(self, ext):
        """
        Get API for given extension
        """
        if hasattr(self, ext):
            return getattr(self, ext)
        if not ext in self._plugins:
            self._plugins[ext] = plugin.get_plugin(ext)[-2]()
            self._plugins[ext]._extension_connect(self)
            self._plugins[ext]._extension_activate()
        return self._plugins.get(ext)

    def get_extension_by_namespace(self, ns):
        """
        Return the plugin for the given extension.
        """
        return self.get_extension(plugin.get_plugin_by_namespace(ns))

    @property
    def extensions(self):
        """
        Get all supported extensions after a query.
        """
        return plugin.extensions(self.disco.features)

    def shutdown(self):
        """
        Shutdown all plugins. The node is unsuable after calling this function
        """
        for p in self._plugins.values():
            p._extension_shutdown()
        for p in self._plugins.values():
            p._extension_disconnect()
        self._plugins = {}

    def __del__(self):
        """
        Delete function for debugging
        """
        print 'gc delete %s' % self.jid
