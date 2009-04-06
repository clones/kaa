# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# jingle_streams.py - XEP-0247: Jingle XML Streams
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.xmpp - XMPP framework for the Kaa Media Repository
# Copyright (C) 2008-2009 Dirk Meyer
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

    requires = [ 'jingle', 'e2e-streams', 'xtls', 'jingle-ibb' ]

    @kaa.coroutine()
    def connect(self):
        """
        Open new secure connection
        """
        description = xmpp.Element('description', xmlns=NS_XMLSTREAM)
        session = self.get_extension('jingle').create_session('xmlstream', description, 'jingle-ibb', 'xtls')
        session.description_ready()
        if not (yield session.initiate()):
            raise RuntimeError('error during e2e-streams connect to %s' % self.remote.jid)
        log.info('jingle initiator ready')
        stream = self.get_extension('e2e-streams').create_stream(session.socket)
        stream.connect()
        stream.properties['secure'] = True
        stream.properties['peer-certificate'] = session.cert
        if (yield stream.signals.subset('connected', 'closed').any())[0]:
            # closed before connected
            raise RuntimeError('error during e2e-streams connect to %s' % self.remote.jid)
        # override stream object of RemoteNode
        self.remote.stream = stream


class Responder(xmpp.ClientPlugin):

    requires = [ 'jingle', 'e2e-streams', 'xtls', 'jingle-ibb' ]

    @kaa.coroutine()
    def jingle_session_initiate(self, session):
        session.description_ready()
        if not (yield session.accept()):
            log.error('error on jingle session setup')
            yield None
        log.info('jingle responder ready')
        initiator = self.client.get_node(session.initiator)
        stream = self.get_extension('e2e-streams').create_stream(session.socket, initiator)
        stream.properties['secure'] = True
        stream.properties['peer-certificate'] = session.cert
        # override stream object
        self.client.get_node(stream.routing.get('from')).stream = stream

# register extension plugin
xmpp.add_extension('jingle-streams', NS_XMLSTREAM, Responder, Initiator)
