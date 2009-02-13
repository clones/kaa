# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# jingle.py - XEP-0166: Jingle
# -----------------------------------------------------------------------------
# $Id$
#
# Status: experimental
# Todo: This module can only handle IBB based transports and can only
#   create a session. No complex session negotiation is possible, not
#   even session shutdown. This module needs much more love.
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

__all__ = [ 'Session', 'Initiator', 'Responder', 'NS_JINGLE' ]

# python imports
import logging

# kaa imports
import kaa
from .. import api as xmpp

# get logging object
log = logging.getLogger('xmpp')

#: Jingle namespace
NS_JINGLE = 'urn:xmpp:tmp:jingle'

class Session(object):
    """
    Jingle Session handling
    """
    STATE_PENDING = 'STATE_PENDING'
    STATE_ACTIVE = 'STATE_ACTIVE'
    STATE_ENDED = 'STATE_ENDED'

    def __init__(self, xmppnode, sid, initiator, content):
        """
        Create jingle session
        """
        #: Session Signal: C{state-change}
        self.signals = kaa.Signals('state-change')
        #: current state
        self.state = Session.STATE_PENDING
        #: peer object
        self.xmppnode = xmppnode
        #: initiator jid
        self.initiator = initiator
        #: session id
        self.sid = sid
        #: jingle content
        self.content = content

    def _send(self, action, content):
        """
        Send jingle iq stanza
        """
        return self.xmppnode.iqset('jingle', xmlns=NS_JINGLE, action=action,
            initiator=self.initiator, sid=self.sid, content=content)

    @kaa.coroutine()
    def initiate(self):
        """
        Send session-initiate
        """
        try:
            yield self._send('session-initiate', self.content)
        except Exception, e:
            log.exception('session-initiate')
            self.state = Session.STATE_ENDED
            self.signals['state-change'].emit()
            yield False
        yield True

    @kaa.coroutine()
    def accept(self):
        """
        Send session-accept
        """
        yield self._send('session-accept', self.content)
        self.state = Session.STATE_ACTIVE
        self.signals['state-change'].emit()

    def close(self):
        log.debug('jingle session closed')
        # FIXME: signal this to the peer
        self.state = Session.STATE_ENDED
        self.signals['state-change'].emit()


class Initiator(xmpp.RemotePlugin):
    """
    Initiator of a jingle session (RemoteNode plugin)
    """
    def create_session(self, sid, name, description, transport):
        """
        Create a new session

        :param sid: session id
        :param name: application name
        :param description: description XML object
        :param transport: transport XML object
        """
        content = xmpp.Element('content', creator='initiator', name=name, content=[ description, transport ])
        session = Session(self.remote, sid, self.client.jid, content)
        self._sessions[sid] = session
        return session

    def get_session(self, sid):
        """
        Get the session object for the given sid or None if not found.

        :param sid: session id
        """
        return self._sessions.get(sid)

    def _extension_activate(self):
        """
        Activate the extension
        """
        self._sessions = {}

    def _extension_shutdown(self):
        """
        Shutdown the extension
        """
        self._sessions = {}


class Responder(xmpp.ClientPlugin):
    """
    Initiator to a jingle session-initiate (Client plugin)
    """
    def __init__(self):
        self.applications = {}

    def register(self, application, callback):
        """
        Register an application callback for session-initiate
        """
        self.applications[application] = callback

    def get_session(self, jid, sid):
        """
        Get the session object for the given sid or None if not found.

        :param jid: peer jid
        :param sid: session id
        """
        node = self.client.get_node(jid, create=False)
        if not node:
            return None
        return node.get_extension('jingle').get_session(sid)

    @xmpp.iq(xmlns=NS_JINGLE)
    def _handle_jingle(self, jid, stanza, const, stream):
        """
        @bug: this function calls get_node all the time and this could lead
            kaa.xmpp using a lot of memory
        """
        sid = stanza.sid
        if stanza.action == 'session-initiate':
            content = stanza.content
            if not content.name in self.applications:
                raise xmpp.CancelException('service-unavailable')
            session = Session(self.client.get_node(jid), sid, jid, content)
            self.client.get_node(jid).get_extension('jingle')._sessions[sid] = session
            if not self.applications[content.name](session):
                raise xmpp.CancelException('service-unavailable')
            return xmpp.Result(None)
        if stanza.action == 'session-accept':
            session = self.get_session(jid, sid)
            session.state = Session.STATE_ACTIVE
            session.signals['state-change'].emit()
            return xmpp.Result(None)
        # FIXME: handle shutdown
        raise NotImplementedError


# register extension
xmpp.add_extension('jingle', NS_JINGLE, Responder, Initiator)
