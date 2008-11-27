# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# jingle_streams.py - XEP-0247: Jingle XML Streams
# -----------------------------------------------------------------------------
# $Id$
#
# Status: Working
# Todo: Add secure session shutdown (depends in jingle.py)
#       Notify callback on failed connect
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
from .. import api as xmpp

# get logging object
log = logging.getLogger('xmpp')

# namespace definition
NS_XMLSTREAM = 'urn:xmpp:tmp:jingle:apps:xmlstream'

class Initiator(xmpp.RemotePlugin):

    requires = [ 'ibb', 'jingle', 'e2e-streams' ]

    @kaa.coroutine()
    def connect(self):
        """
        Open new secure connection
        """
        description = xmpp.Element(
            'description', xmlns=NS_XMLSTREAM, authentication='optional',
            disclosure='never', logging='mustnot', tls='required')
        transport = self.get_extension('ibb')
        session = self.get_extension('jingle').create_session(
            'SID', 'xmlstream', description, transport.jingle_transport())
        transport.jingle_listen(session)
        session.initiate()
        yield session.signals.subset('state-change').any()
        stream = self.get_extension('e2e-streams').create_stream(session.socket)
        stream.connect()
        transport.signals['closed'].connect(session.close)
        if (yield stream.signals.subset('connected', 'closed').any())[0]:
            # closed before connected
            raise RuntimeError('error during e2e-streams connect to %s' % self.remote.jid)
        # override stream object of RemoteNode
        self.remote.stream = stream


class Responder(xmpp.ClientPlugin):

    requires = [ 'ibb', 'jingle', 'e2e-streams' ]

    def _extension_activate(self):
        self.get_extension('jingle').register('xmlstream', self.jingle_session_initiate)

    @kaa.coroutine()
    def jingle_session_initiate(self, session):
        if session.content.transport.xmlns == 'urn:xmpp:tmp:jingle:transports:ibb':
            transport = self.client.get_node(session.initiator).get_extension('ibb')
        else:
            # FIXME: add error handling, replace session
            # This code should move into jingle.py
            yield False
        yield transport.jingle_open(session)
        yield session.accept()
        transport.signals['closed'].connect(session.close)
        e2e = self.get_extension('e2e-streams')
        initiator = self.client.get_node(session.initiator)
        stream = yield e2e.new_connection(session.socket, initiator)

# register extension plugin
xmpp.add_extension('jingle-streams', NS_XMLSTREAM, Responder, Initiator)
