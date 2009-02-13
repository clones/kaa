# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# pubsub.py - PubSub (XEP-0060) plugin
# -----------------------------------------------------------------------------
# $Id$
#
# Status: This plugin implements some parts of a PubSub client. When
#    PEP is implemented this plugin needs to provide some information
#    to PEP. This module needs much more love.
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

__all__ = [ 'NS_PUBSUB', 'PubSub', 'Node' ]

# python imports
import logging
from functools import partial as inherit

# kaa imports
import kaa
from .. import api as xmpp

# get logging object
log = logging.getLogger('xmpp')

#: pubsub namespace
NS_PUBSUB = 'http://jabber.org/protocol/pubsub'
NS_PUBSUB_EVENT = 'http://jabber.org/protocol/pubsub#event'

#: disco#info namespace
NS_DISCO  = 'http://jabber.org/protocol/disco'


class Node(object):
    """
    PubSub interface for a node on the server
    """
    def __init__(self, client, server, node):
        """
        Create Node
        """
        # inherit pubsub send function
        self._send = inherit(client.iqset, 'pubsub', to=server)
        #: node name
        self.name = node

    def discovery_info(self):
        """
        Query node (XEP-0030)
        """
        cmd = xmpp.Element('query', node=self.name)
        return self._send(xmlns=NS_DISCO+'#info', content=cmd)

    def configure(self):
        """
        """
        return self._send(xmlns=NS_DISCO+'#owner', content=xmpp.Element('configure', node=self.name))

    def subscriptions(self):
        """
        """
        return self._send(xmlns=NS_DISCO+'#owner', content=xmpp.Element('subscriptions', node=self.name))

    #
    # Node handling
    #

    @kaa.coroutine()
    def create(self):
        """
        Create the node. Returns an InProgress object
        """
        cmd = [
            xmpp.Element('create', node=self.name),
            xmpp.Element('configure')
        ]
        try:
            yield self._send(xmlns=NS_PUBSUB, content=cmd)
        except xmpp.XMPPException, e:
            if e.code != 409:
                # ignore error that the node is already created
                raise e

    def delete(self):
        """
        Delete the node. Returns an InProgress object
        """
        cmd = xmpp.Element('delete', node=self.name)
        return self._send(xmlns=NS_PUBSUB + '#owner', content=cmd)

    def subscribe(self, jid):
        """
        Subscribe to the node with the given jid. Returns an
        InProgress object
        """
        cmd = xmpp.Element('subscribe', node=self.name, jid=jid)
        return self._send(xmlns=NS_PUBSUB, content=cmd)


    #
    # Item handling
    #

    def publish(self, item, id):
        """
        Add a new item (xmpp.Element) with the given id. Returns an
        InProgress object
        """
        cmd = xmpp.Element('publish', node=self.name)
        cmd.add_child('item', id=id, content=item)
        return self._send(xmlns=NS_PUBSUB, content=cmd)

    def delete(self, id):
        """
        Delete item with the given id. Returns an InProgress object
        """
        cmd = xmpp.Element('retract', node=self.name)
        cmd.add_child('item', id=id)
        return self._send(xmlns=NS_PUBSUB, content=cmd)

    @kaa.coroutine()
    def items(self, max_items=0):
        """
        Get all items. If max_items is greater than zero, return a list
        with maximal max_items entries.
        """
        cmd = xmpp.Element('items', max_items=(max_items or None), node=self.name)
        items = yield self._send(xmlns=NS_PUBSUB, content=cmd)
        yield items.get_child('items').get_children()


class Event(object):
    """
    PubSub event
    """
    def __init__(self, sender, node, item):
        self.id = item.id
        self.sender = sender
        self.node = node
        self.event = item.get_children()[0]


class PubSub(xmpp.ClientPlugin):
    """
    PubSub interface for the given PubSub server (RemoteNode)
    """
    def __init__(self):
        """
        PubSub interface for the RemoteNode
        """
        self.signals = kaa.Signals('event', 'delete')
        self._server = {}

    def get_node(self, server, name):
        """
        Return the node with the given name on the provided server. If
        server is None, PEP on the user's server is used.
        """
        if not server in self._server:
            self._server[server] = {}
        if not name in self._server[server]:
            self._server[server][name] = Node(self.client, server, name)
        return self._server[server][name]

    @xmpp.message(xmlns=NS_PUBSUB_EVENT)
    def _handle_event(self, jid, event, stream):
        """
        PubSub callback from the server.
        """
        for item in event.items.get_children('item'):
            e = Event(jid, event.items.node, item)
            self.signals['event'].emit(e)

    @xmpp.message(xmlns=NS_PUBSUB_EVENT)
    def _handle_x(self, jid, msg, stream):
        """
        PubSub callback from the server.
        """
        # get the correct node and emit the signal
        name = msg.get_child('items')['node']
        if not name in self._nodes:
            log.warning('event from unkown node %s', name)
        node = self.get_node(name)
        for item in msg.get_child('items').get_children('retract'):
            node.signals['del'].emit(item['id'])

# register extension plugin
xmpp.add_extension('pubsub', None, PubSub, None)
