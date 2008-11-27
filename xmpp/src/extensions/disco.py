# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# disco.py - XEP-0030: Service Discovery
#            XEP-0115: Entity Capabilities
# -----------------------------------------------------------------------------
# $Id$
#
# Status: Only disco#info implemented
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

__all__ = [ 'NS_DISCO_INFO', 'NS_CAPS', 'RemoteNode', 'Client' ]

# python imports
import hashlib
import kaa

# import kaa.xmpp api
from .. import api as xmpp

#: namespace for this extension
NS_DISCO_INFO = 'http://jabber.org/protocol/disco#info'
NS_CAPS = 'http://jabber.org/protocol/caps'

class RemoteNode(xmpp.RemotePlugin):
    """
    Service Discovery for a remote entity.
    """
    @kaa.coroutine()
    def query(self):
        """
        Service Discovery (XEP-0030) disco#info
        """
        r = yield self.remote.iqget('query', xmlns=NS_DISCO_INFO)
        self.cache.features = []
        for feature in r.get_children('feature'):
            self.cache.features.append(feature['var'])
        yield self.cache.features

    @property
    def features(self):
        """
        List all supported features based on a query
        """
        return self.cache.features


class Client(xmpp.ClientPlugin):
    """
    Service Discovery implementation for the client.
    """

    identities = [ ('client', 'bot') ]

    @xmpp.iq(xmlns=NS_DISCO_INFO)
    def _handle_query(self, jid, stanza, const, stream):
        """
        Service Discovery disco#info callback
        """
        result = xmpp.Result('query', xmlns=NS_DISCO_INFO)
        for c, t in self.identities:
            result.add_child('identity', category=c, type=t, name=self.client.appname)
        for feature in self.client.features:
            result.add_child('feature', var=feature)
        return result

    @property
    def capabilities(self):
        """
        Return capabilities ver hash.
        """
        ver = ''
        for c, t in self.identities:
            ver += '%s/%s/%s<' % (c, t, self.client.appname)
        self.client.features.sort()
        ver += '<'.join(self.client.features)
        return hashlib.sha1(ver + '<').hexdigest()


# register extension
xmpp.add_extension('disco', [ NS_DISCO_INFO, NS_CAPS ], Client, RemoteNode, True)
