# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# ibb.py - In-band bytestream (XEP-0047) plugin
# -----------------------------------------------------------------------------
# $Id$
#
# A client must activate the 'ibb' extension to make In-Band
# Bytestreams possible. A different protocol must be used to exchange
# the sid of the stream. One side has to call 'open', the other side
# 'listen'. It will return a kaa.Socket on both ends. Closing the
# socket will close the bytestream.
#
# Status: mostly completed
# Todo: IBB over message stanzas not implemented
#       close not fully tested
#       add presence support for close
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

__all__ = [ 'IBBSocket', 'IBB', 'Client', 'NS_IBB' ]

# python imports
import logging
import base64
from functools import partial as inherit

# kaa imports
import kaa
from .. import api as xmpp

# get logging object
log = logging.getLogger('xmpp')

#: Namespace for In-Band Bytestreams
NS_IBB = 'http://jabber.org/protocol/ibb'

class IBBSocket(object):
    """
    IBB to Socket handler.
    """
    def __init__(self, socket, iq, sid, blocksize, stream):
        """
        Create IBBSocket to link a socket with XMPP
        """
        self.sid = sid
        self._socket = socket
        self._socket.signals['read'].connect(self.read)
        self._send = inherit(iq, xmlns=NS_IBB, sid=sid, xmppstream=stream)
        self._bs = int(blocksize)
        self._send_seq = 0
        self._recv_seq = 0

    def send(self, data):
        """
        Send data from XMPP to the socket. The provided data is the
        XMPP transport stanza (iq)
        """
        if self._socket == None:
            log.error('socket closed')
            return
        if int(data.get('seq')) != self._recv_seq:
            self.close()
            raise IOError('bad sequence')
        self._recv_seq += 1
        self._socket.write(base64.b64decode(data.content))

    def close(self, arg=None):
        """
        Closed by application connected to the socket
        """
        if self._socket is None:
            return
        log.debug('IBB closed by application layer')
        try:
            self._send(tagname='close')
        except Exception, e:
            log.debug('IBB close error')
        self._close()

    def _close(self, arg=None):
        """
        Closed by XMPP layer.
        """
        if self._socket is None:
            return
        # close socket, this will trigger close on the other socket
        self._socket.signals['read'].disconnect(self.read)
        self._socket.signals['closed'].disconnect(self.close)
        self._socket.close()
        self._send = None
        self._socket = None

    def read(self, data):
        """
        Read data from the UNIX domain socket and send it to the XMPP
        layer.
        """
        data = base64.b64encode(data)
        while data:
            block = data[:self._bs]
            data = data[self._bs:]
            self._send(tagname='data', seq=self._send_seq, content=block)
            self._send_seq += 1


class IBB(xmpp.RemotePlugin):
    """
    IBB (XEP-0047) Plugin
    """
    def __init__(self):
        """
        Create a new In-Band Bytestream to the RemoteNode
        """
        self.signals = kaa.Signals('closed')
        self.callbacks = {}
        self._streams = {}

    def _extension_shutdown(self):
        """
        Shutdown the plugin.
        """
        self.callbacks = {}
        # close all streams
        for stream in self._streams.values():
            stream.close()
        self._streams = {}

    @kaa.coroutine()
    def open(self, sid, blocksize=4096):
        """
        Open a new IBB.
        """
        attr = {'sid': sid, 'block-size': blocksize}
        yield self.remote.iqset('open', xmlns=NS_IBB, **attr)
        socket, ibb = yield self._create(sid, blocksize, self.remote.stream)
        self._streams[sid] = ibb
        yield socket

    def listen(self, sid, callback):
        """
        Register callback to be called when IBB sid is opened
        """
        self.callbacks[sid] = callback

    @kaa.coroutine()
    def jingle_open(self, session):
        """
        Jingle integration: open a session
        """
        socket = yield self.open(session.sid)
        session.socket = socket

    def jingle_listen(self, session):
        """
        Jingle integration: listing to incoming connection
        """
        self.listen(session.sid, lambda socket: setattr(session, 'socket', socket))

    def jingle_transport(self):
        """
        Jingle integration: transport description
        """
        return xmpp.Element('transport', xmlns='urn:xmpp:tmp:jingle:transports:ibb')

    @kaa.coroutine()
    def _handle_open(self, jid, stanza, const, stream):
        """
        Open request from remote node
        """
        if not stanza.sid in self.callbacks:
            # bytestream with the given sid not expected
            yield xmpp.Error(501, 'cancel')
        socket, ibb = yield self._create(stanza.sid, stanza.get('block-size'), stream)
        self._streams[stanza.sid] = ibb
        self.callbacks.pop(stanza.sid)(socket)
        yield xmpp.Result(None)

    @kaa.coroutine()
    def _create(self, sid, blocksize, stream):
        """
        Create the FIFO and return the kaa.Socket and the IBBSocket object.
        """
        # Make a kaa.Socket to kaa.Socket connection. One socket will be
        # given to the outside, the other one will be used to communicate
        # with the IBBSocket.
        filename = kaa.tempfile('ibb', unique=True)
        socket1 = kaa.net.tls.TLSSocket()
        wait = kaa.inprogress(socket1.signals['new-client'])
        socket2 = kaa.Socket()
        socket1.listen(filename)
        yield socket2.connect(filename)
        socket1 = yield wait
        socket1.sid = sid
        socket2.signals['closed'].connect(self._app_close, sid)
        yield socket1, IBBSocket(socket2, self.remote.iqset, sid, blocksize, stream)

    @xmpp.iq(xmlns=NS_IBB)
    def _handle_data(self, stanza, const, stream):
        """
        Data received from the remote node.
        """
        if not stanza.sid in self._streams:
            log.error('data for unknown sid %s', stanza.sid)
            return xmpp.Error(501, 'cancel')
        self._streams[stanza.sid].send(stanza)
        return xmpp.Result(None)

    def _app_close(self, dummy, sid):
        """
        Remote node closed the IBB.
        """
        stream = self._streams.pop(sid, None)
        if stream is not None:
            stream.close()
            self.signals['closed'].emit()

    @xmpp.iq(xmlns=NS_IBB)
    def _handle_close(self, stanza, const, stream):
        """
        Remote node closed the IBB.
        """
        stream = self._streams.pop(stanza.sid, None)
        if stream is not None:
            log.debug('IBB closed by XMPP peer')
            stream._close()
            self.signals['closed'].emit()
        return xmpp.Result(None)


class Client(xmpp.ClientPlugin):

    @xmpp.iq(xmlns=NS_IBB)
    def _handle_open(self, jid, stanza, const, stream):
        """
        Open request from remote node
        """
        remote = self.client.get_node(jid, create=False)
        if not remote:
            # Do not create RemoteNode object if it does not exist. A not
            # existing object can not know about the jid/sid combination
            return xmpp.Error(501, 'cancel')
        return remote.get_extension('ibb')._handle_open(jid, stanza, const, stream)

    def listen(self, jid, sid, callback):
        """
        Register callback to be called when an In-Band Bytestream from
        the given JID with the given SID is opened.
        """
        return self.client.get_node(jid).get_extension('ibb').listen(sid, callback)


# register extension plugin
xmpp.add_extension('ibb', NS_IBB, Client, IBB)
