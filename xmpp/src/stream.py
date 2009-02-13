# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# stream.py - XMPP stream and connection handling
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
XMPP Stream Class
"""

__all__ = [ 'XMPPStream' ]

# python imports
import sys
import traceback
import logging

# kaa imports
import kaa
import kaa.net.tls

# kaa.xmpp imports
import parser as xmpp
from element import IQ, Result, Error
from error import *

# get logging object
log = logging.getLogger('xmpp')

# special XML logger. The client-> server stream is printed green, the
# server->client stream is red.
DEBUG_XML = False

NS_CLIENT = 'jabber:client'
NS_STREAM = 'http://etherx.jabber.org/streams'
NS_STANZA = 'urn:ietf:params:xml:ns:xmpp-stanzas'

class Callbacks(dict):
    def __init__(self):
        signal = None
        for key in ('stanza', 'message', 'iq'):
            self[key] = xmpp.Callbacks(key)

    def connect(self, obj, jid=None):
        for key in self.keys():
            self[key].connect(obj, jid)

    def disconnect(self, obj, jid=None):
        for key in self.keys():
            self[key].disconnect(obj, jid)


class XMPPStream(object):
    """
    Class to manage XML streams, the connection, TLS and basic stanza parsing.
    It represents a link between client and server. Right now this class can
    only be used on client side.
    """

    NOT_CONNECTED = 'NOT_CONNECTED'
    CONNECTING = 'CONNECTING'
    CONNECTED = 'CONNECTED'

    def __init__(self):
        self.signals = kaa.Signals(
            'connected',                # stream is ready for iq/messages
            'error',                    # global stream error
            'closed',                   # stream is closed
            'message'                   # unhandled message
        )
        self.status = XMPPStream.NOT_CONNECTED
        self._socket = None
        self._greeting = None
        self._featurelist = {}
        self._iqlist = {}
        self._parser = None
        self._client_callbacks = Callbacks()
        self._stream_callbacks = Callbacks()
        self._stream_callbacks.connect(self)
        self.properties = {}

    def _get_callback(self, type, name, xmlns, jid=None):
        is_remote_cb = False
        callback = self._stream_callbacks[type].get(name, xmlns, jid)
        if jid is not None:
            callback, is_remote_cb = callback
        if callback is None:
            callback = self._client_callbacks[type].get(name, xmlns, jid)
            if jid is not None:
                callback, is_remote_cb = callback
        return callback, is_remote_cb

    def connect(self, address):
        """
        Connect to the given host/port address
        """
        self.status = XMPPStream.CONNECTING
        # open connection to addr
        if self._greeting is None:
            self._greeting = '''<?xml version="1.0"?>
            <stream:stream to="%s" xmlns="jabber:client"
            xmlns:stream="http://etherx.jabber.org/streams"
            version="1.0">''' % address[0]
        self._socket = kaa.net.tls.TLSSocket()
        self._socket.connect(address).connect(self.restart)

    def _connected(self):
        """
        Callback when stream is connected.
        """
        self.status = XMPPStream.CONNECTED
        self.signals['connected'].emit()

    def restart(self, *args, **kwargs):
        """
        (Re)start the stream.
        """
        if self._parser:
            # disconnect old, now useless parser
            self._socket.signals['read'].disconnect(self._parser.parse)
            self._parser.signals['invalid'].disconnect(self.close)
        self._parser = xmpp.XMLStreamParser(self._handle_stanza)
        self._socket.signals['read'].connect(self._parser.parse)
        self._parser.signals['invalid'].connect(self.close)
        if isinstance(self._greeting, (str, unicode)):
            self._socket.write(self._greeting)

    def send(self, data, feature_negotiation=False):
        """
        Send a stanza to the server.
        """
        if not self._socket:
            return
        if isinstance(data, IQ):
            self._iqlist[data.id] = data
        if hasattr(data, '__xml__'):
            data = data.__xml__()
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        if DEBUG_XML:
            print '\033[1;32m%s\033[1;m' % data
        self._socket.write(data)

    def close(self, stream_close=True):
        """
        Close the XMPP connection.
        """
        log.info('close stream')
        if self._parser:
            # disconnect parser
            self._socket.signals['read'].disconnect(self._parser.parse)
            self._parser.signals['invalid'].disconnect(self.close)
            self._parser = None
        if not self._socket:
            return
        if stream_close:
            self.send('</stream>', feature_negotiation=True)
        self._socket.close()
        self._socket = None
        self.signals['closed'].emit()

    @kaa.coroutine()
    def starttls(self, key=None, srp=None, checker=None):
        """
        Start TLS on the socket.

        :param cert: TLSKey object for client authentication
        :param srp: username, password pair for SRP authentication
        :param checker: callback to check the credentials from the server
        """
        yield self._socket.starttls_client(key=key, srp=srp, checker=checker)
        self.restart()

    def xmpp_connect(self, obj, jid=None, private=False):
        """
        Connect XMPP callbacks in the given object.
        """
        if private:
            return self._stream_callbacks.connect(obj, jid)
        self._client_callbacks.connect(obj, jid)

    def xmpp_disconnect(self, obj, jid=None, private=False):
        """
        Connect XMPP callbacks in the given object.
        """
        if private:
            return self._stream_callbacks.disconnect(obj, jid)
        self._client_callbacks.disconnect(obj, jid)

    def add_feature(self, feature):
        """
        Add a feature to the stream.
        """
        # FIXME: this needs a rewrite
        self._featurelist['::'.join(feature.identifier)] = feature

    def _handle_stanza(self, name, xmlns, stanza):
        """
        Generic stream stanza callback.
        """
        if DEBUG_XML:
            print '\033[1;31m%s\033[1;m' % stanza
        callback, is_jid_cb = self._get_callback('stanza', name, xmlns)
        try:
            if callback is not None:
                return callback(stanza)
        except Exception, e:
            return log.exception('stanza error')
        if (name, xmlns) != ('stream', 'http://etherx.jabber.org/streams'):
            log.error('no handler for %s:%s', name, xmlns)

    @xmpp.stanza(xmlns=NS_STREAM)
    def _handle_error(self, error):
        """
        Global stream error, the link to the server will be closed.
        """
        log.error(error)
        self.signals['error'].emit(error)
        self._socket.close()
        self._socket = None
        self.signals['closed'].emit()

    @xmpp.stanza(xmlns=NS_CLIENT, coroutine=True)
    def _handle_iq(self, iq):
        """
        Callback for the <iq> stanza.
        """
        type = iq.get('type', 'get')
        if type in ('result', 'error'):
            if not iq['id'] in self._iqlist:
                log.error('got result for unknown iq %s', iq['id'])
            else:
                self._handle_iq_result(iq)
        else:
            yield self._handle_iq_request(iq)

    @kaa.coroutine()
    def _handle_iq_request(self, iq):
        """
        Callback for the <iq> get or set stanza.
        """
        entity = iq.get('from')
        # get callback based on node name, namespace and jid
        stanza = iq.get_children()[0]
        cb, remote = self._get_callback('iq', stanza.tagname, stanza.xmlns, entity)
        try:
            if not cb:
                log.error('no handler for\n%s' % iq)
                raise NotImplementedError()
            # print cb.im_func.func_code.co_varnames
            # FIXME: message from server is verified
            if remote:
                result = cb(stanza, iq.get('type') == 'get', self)
            else:
                result = cb(entity, stanza, iq.get('type') == 'get', self)
            if isinstance(result, kaa.InProgress):
                result = yield result
            if result is None:
                result = Result(None)
            if not isinstance(result, (Result, Error)):
                log.error('No return for %s', iq)
                return
        except (SystemExit, KeyboardInterrupt), e:
            raise e
        except Exception, e:
            log.exception(e)
            cls, name, trace = sys.exc_info()
            result = Error(500, 'cancel')
            if cls == NotImplementedError:
                result.add_child('feature-not-implemented', NS_STANZA)
            elif cls == CancelException:
                result.add_child(name, NS_STANZA)
            else:
                trace = ''.join(traceback.format_exception(cls, e, trace)).strip()
                result.add_child('undefined-condition')
                result.add_child('text', content=str(e))
                result.add_child('trace', content=trace)
        result.set_request(iq)
        self.send(result)

    def _handle_iq_result(self, iq):
        """
        Callback for the <iq> stanza results (result/error)
        """
        if iq.get('type') == 'result':
            # it is a result, send it to the waiting IQ
            async = self._iqlist.pop(iq['id'])
            if len(iq.get_children()):
                # return first child as result
                return async.finish(iq.get_children()[0])
            # return None as result
            return async.finish(None)
        # it is an error, throw it at the waiting IQ
        async = self._iqlist.pop(iq['id'])
        error = iq.get_child('error')
        try:
            if error.has_child('feature-not-implemented'):
                e = '\'%s\' in \'%s\' unsupported' % (async.tagname, async.xmlns)
                raise XMPPNotImplementedError(e)
            if error.has_child('recipient-unavailable'):
                raise XMPPRecipientUnavailableError('remote node not connected')
            if error.has_child('text') and error.has_child('trace'):
                raise XMPPTracebackError(error)
            raise XMPPException(error)
        except XMPPException, e:
            async.throw(e.__class__, e, None)

    @xmpp.stanza(xmlns=NS_CLIENT)
    def _handle_message(self, msg):
        """
        Callback for the <message> stanza.
        """
        try:
            entity = msg.get('from')
            # get callback based on node name, namespace and jid
            stanza = msg.get_children()[0]
            cb, remote = self._get_callback('message', stanza.tagname, stanza.xmlns, entity)
            if remote:
                return cb(stanza, self)
            if not cb:
                # FIXME: signals should be client specific
                cb = self.signals['message'].emit
            cb(entity, stanza, self)
        except (SystemExit, KeyboardInterrupt), e:
            raise e
        except Exception, e:
            log.exception(e)

    @xmpp.stanza(xmlns=NS_STREAM, coroutine=True)
    def _handle_features(self, features):
        """
        Callback for the <features> stanza.
        """
        # FIXME: this needs a rewrite
        for f in features:
            name = '::'.join((f.tagname, f.xmlns))
            if not name in self._featurelist:
                log.info('ignore stream feature %s' % name)
                continue
            log.info('process stream feature %s' % name)
            parser = self._parser
            feature = self._featurelist[name]
            try:
                self.xmpp_connect(feature, private=True)
                yield feature.run(f)
            except Exception:
                self.xmpp_disconnect(feature, private=True)
                log.exception('unhandled error in feature negotiation, close stream')
                self.close()
                yield False
            self.xmpp_disconnect(feature, private=True)
            del self._featurelist[name]
            if parser != self._parser:
                # stream restart
                return
        self._connected()
