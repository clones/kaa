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

# kaa imports
import kaa
import kaa.net.mdns
import kaa.net.tls

# kaa.xmpp imports
from .. import api as xmpp

# get logging object
log = logging.getLogger('xmpp')

class XEP0174(xmpp.ClientPlugin):
    """
    Plugin for XEP-0174: Link-local messaging.
    """

    requires = [ 'e2e-streams', 'disco' ]

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
            self.client.appname, '_presence._tcp', self.get_extension('e2e-streams').port, {
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

# register extension plugin
xmpp.add_extension('link-local', None, XEP0174, None)
