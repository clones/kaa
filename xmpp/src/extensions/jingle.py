# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# jingle.py - XEP-0166: Jingle
# -----------------------------------------------------------------------------
# $Id$
#
# Status: experimental
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

MODULE_DESCRIPTION = 'description'
MODULE_TRANSPORT = 'transport'
MODULE_SECURITY = 'security'

class Session(object):
    """
    Jingle Session handling
    """
    STATE_PENDING = 'STATE_PENDING'
    STATE_ACTIVE = 'STATE_ACTIVE'
    STATE_ENDED = 'STATE_ENDED'

    def __init__(self, remote, sid, initiator, security):
        """
        Create jingle session
        """
        #: Session Signal: C{state-change}
        self.signals = kaa.Signals('state-change')
        #: current state
        self.state = Session.STATE_PENDING
        #: peer object
        self.remote = remote
        #: initiator jid
        self.initiator = initiator
        #: session id
        self.sid = sid
        self.initializing = [ MODULE_TRANSPORT, MODULE_DESCRIPTION ]
        if security:
            self.initializing.append(MODULE_SECURITY)
        #: plugins
        self.transport = None
        self.security = None

    def prepare(self, content):
        self._content = content
        return self

    def _send(self, action, content):
        """
        Send jingle iq stanza
        """
        return self.remote.iqset('jingle', xmlns=NS_JINGLE, action=action,
            initiator=self.initiator, sid=self.sid, content=content)

    def description_ready(self):
        self.initializing.remove(MODULE_DESCRIPTION)
        if not self.initializing:
            self.state = Session.STATE_ACTIVE
            self.signals['state-change'].emit()

    def transport_ready(self):
        self.initializing.remove(MODULE_TRANSPORT)
        if not self.initializing:
            self.state = Session.STATE_ACTIVE
            self.signals['state-change'].emit()
        if MODULE_SECURITY in self.initializing:
            self.security.jingle_transport_ready(self)

    def security_ready(self):
        self.initializing.remove(MODULE_SECURITY)
        if not self.initializing:
            self.state = Session.STATE_ACTIVE
            self.signals['state-change'].emit()

    def security_info(self, info):
        self._send('security-info', xmpp.Element('content', content=info))

    def close(self):
        log.debug('jingle session closed')
        # FIXME: signal this to the peer
        self.state = Session.STATE_ENDED
        self.signals['state-change'].emit()


class InitiatorSession(Session):

    @kaa.coroutine()
    def initiate(self):
        """
        Send session-initiate and return InProgress object that will
        be done once the session is ready to be used or failed.
        """
        try:
            yield self._send('session-initiate', self._content)
        except Exception, e:
            log.exception('session-initiate')
            self.state = Session.STATE_ENDED
            self.signals['state-change'].emit()
        finally:
            del self._content
        if self.state == Session.STATE_PENDING:
            yield self.signals.subset('state-change').any()
        yield self.state == Session.STATE_ACTIVE


class ResponderSession(Session):

    @kaa.coroutine()
    def accept(self):
        """
        """
        content = [ self._content.description ]
        self.transport = self.remote.get_extension_by_namespace(self._content.transport.xmlns)
        if not self.transport:
            raise RuntimeError('FIXME: handle unsupported transport')
        content.append(self.transport.jingle_accept(self, self._content.transport))
        if self._content.security:
            self.security = self.remote.get_extension_by_namespace(self._content.security.xmlns)
            if not self.security:
                raise RuntimeError('FIXME: handle unsupported security')
            content.append(self.security.jingle_accept(self, self._content.security))
        content = xmpp.Element('content', creator='initiator', name=self._content.creator, content=content)
        yield self._send('session-accept', content)
        if self.state == Session.STATE_PENDING:
            yield self.signals.subset('state-change').any()
        yield self.state == Session.STATE_ACTIVE


class Initiator(xmpp.RemotePlugin):
    """
    Initiator of a jingle session (RemoteNode plugin)
    """
    def create_session(self, name, description, transport, security=None):
        """
        Create a new session

        :param name: application name
        :param description: description XML object
        :param transport: transport XML object
        :param security: security XML object
        """
        sid = xmpp.create_id()
        session = InitiatorSession(self.remote, sid, self.client.jid, security is not None)
        session.transport = self.get_extension(transport)
        content = [ description, session.transport.jingle_initiate(session) ]
        if security:
            session.security = self.get_extension(security)
            content.append(session.security.jingle_initiate(session))
        session.prepare(xmpp.Element('content', creator='initiator', name=name, content=content))
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
            application = self.client.get_extension_by_namespace(content.description.xmlns)
            if application is None:
                raise xmpp.CancelException('service-unavailable')
            remote = self.client.get_node(jid)
            session = ResponderSession(remote, stanza.sid, remote.jid, content.security is not None)
            session.prepare(content)
            remote.get_extension('jingle')._sessions[stanza.sid] = session
            # notify the application and do nothing until we get an accept
            application.jingle_session_initiate(session)
            return xmpp.Result(None)
        if stanza.action == 'session-accept':
            session = self.get_session(jid, sid)
            if not stanza.content.security and session.security:
                raise RuntimeError('FIXME: peer does not support e2e security')
            session.transport.jingle_transport_info(session, stanza.content.transport)
            if session.security:
                session.security.jingle_security_info(session, stanza.content.security)
            return xmpp.Result(None)
        if stanza.action == 'security-info':
            session = self.get_session(jid, sid)
            session.security.jingle_security_info(session, stanza.content.security)
            return xmpp.Result(None)
        # FIXME: handle shutdown
        raise NotImplementedError


# register extension
xmpp.add_extension('jingle', NS_JINGLE, Responder, Initiator)
