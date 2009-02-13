# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# roster.py - Simple Roster and Presence Implementation
# -----------------------------------------------------------------------------
# $Id$
#
# Todo: This module needs a huge cleanup. The signals should move into
#    the client object, user and clients need to be accessable in a
#    easy way, and the module should hook itself into the connect
#    mechanism.
#
# -----------------------------------------------------------------------------
# kaa.xmpp - XMPP framework for the Kaa Media Repository Copyright (C)
# 2008 Dirk Meyer
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

# kaa imports
import kaa
from .. import api as xmpp

# get logging object
log = logging.getLogger('xmpp')

# namespace definitions
NS_ROSTER = 'jabber:iq:roster'
NS_CLIENT = 'jabber:client'


class Contact(object):
    """
    Contact information
    """
    def __init__(self):
        self.clients = []


class Roster(xmpp.ClientPlugin):
    """
    Client.roster class
    """

    requires = [ 'disco' ]

    def __init__(self):
        super(Roster, self).__init__()
        self.signals = kaa.Signals(
            'presence',  # presence update (jid, status, details)
            'update',    # subscription update (jid, none/to/from/both/del)
            'request'    # subscription request (jid)
        )
        self.contacts = {}

    # internal callbacks

    @xmpp.iq(xmlns=NS_ROSTER, coroutine=True)
    def _query(self, jid, node, const, stream):
        """
        Callback for query <iq> push from server
        """
        item = node.get_child('item')
        if item is None:
            log.error('unsupported roster request\n%s', node)
            raise NotImplementedError()
        jid = item.get('jid')
        sub = item.get('subscription')
        if item.get('ask') is not None and sub in ('none', 'to', None):
            self.signals['request'].emit(jid)
        if sub in ('from', 'to', 'both', 'none'):
            if self.contacts.get(jid, None) != sub:
                self.contacts[jid] = sub
                self.signals['update'].emit(jid, sub)
            yield xmpp.Result(None)
        if sub in ('remove',):
            if not jid in self.contacts:
                if self.contacts:
                    log.error('%s not in contact list', jid)
                yield xmpp.Result(None)
            del self.contacts[jid]
            self.signals['update'].emit(jid, 'del')
            yield xmpp.Result(None)
        log.error('unsupported roster request\n%s', node)
        raise NotImplementedError()

    @xmpp.stanza(xmlns=NS_CLIENT)
    def _presence(self, msg):
        """
        Callback for <presence> stanza.
        """
        try:
            jid = msg.get('from')
            if msg.type == 'subscribe':
                # incoming subscription request
                self.signals['request'].emit(jid)
                return
            if msg.type in ('unsubscribed', 'subscribed', 'probe'):
                # ignore this
                return
            # remote node changed presence
            online = msg.type not in ('unavailable', 'unsubscribe', 'error')
            # update contact list
            if jid.find('/') > 0:
                contact = self.contacts.get(jid[:jid.rfind('/')])
                if contact:
                    if online and not jid in contact.clients:
                        contact.clients.append(jid)
                    if not online and jid in contact.clients:
                        contact.clients.remove(jid)
            # signal presence change
            self.signals['presence'].emit(jid, online, msg.get_children())
        except Exception, e:
            log.exception('presence')

    def _send_presence(self, xmmp_from, xmmp_to, **attrs):
        """
        Send <presence> stanza to jid
        """
        if xmmp_from: attrs['from'] = xmmp_from
        if xmmp_to: attrs['to'] = xmmp_to
        self.client.send_stanza(xmpp.Element('presence', **attrs))

    # presence API

    def subscription_request(self, jid):
        """
        Request presence subscription from jid.
        """
        self._send_presence(None, jid, type='subscribe')

    def subscription_accept(self, jid):
        """
        Accept presence subscription request.
        """
        barejid = self.client.jid[:self.client.jid.find('/')]
        self._send_presence(barejid, jid, type='subscribed')

    def register(self):
        """
        Send presence information to set status to available and send
        capabilities (XEP-0115).
        """
        ver = self.get_extension('disco').capabilities
        c = xmpp.Element('c', xmlns='http://jabber.org/protocol/caps', hash='sha-1',
                 node=self.client.appname, ver=ver)
        self._send_presence(self.client.jid, None, content=c)

    # roster API

    @kaa.coroutine()
    def update(self):
        """
        Update list of contacts.
        """
        r = yield self.client.iqget('query', xmlns=NS_ROSTER)
        self.contacts = {}
        for item in r.get_children('item'):
            c = Contact()
            for var in 'subscription', 'name':
                setattr(c, var, item.get(var))
            self.contacts[item['jid']] = c
        yield self.contacts

    def remove(self, jid):
        """
        Remove node from roster and unsubscribe if subscribed.
        """
        item = xmpp.Element('item', jid=jid, subscription='remove')
        self.client.iqset('query', xmlns=NS_ROSTER, content=item)


# register plugin as client.roster
xmpp.add_extension('roster', None, Roster, None, True)
