# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - Wrapper to make CherryPy work with kaa.notifier
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-cherrypy - Web Framework for Kaa based on CherryPy
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'start' ]

# python imports
import socket
import time

# cherrypy imports
import cherrypy._cpwsgiserver
import cherrypy._cpwsgi
import cherrypy._cpserver

# kaa imports
import kaa.notifier

# kaa.cherrypy imports
from config import config


class WSGIServer(cherrypy._cpwsgi.WSGIServer):
    """
    Wrapper class for the real server. It still uses threads but the accept is
    not in a thread anymore, it is async using a SocketDispatcher.
    """
    def start(self):
        """
        Start the server with help of the notifier main loop. Most of this
        code is copied from cherrypy._cpwsgi.WSGIServer.start().
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                                    socket.IPPROTO_TCP)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.bind_addr)
        self.socket.listen(5)

        # Create worker threads
        for i in xrange(self.numthreads):
            self._workerThreads.append(cherrypy._cpwsgiserver.WorkerThread(self))
        for worker in self._workerThreads:
            worker.start()
        for worker in self._workerThreads:
            while not worker.ready:
                time.sleep(.1)

        self.ready = True
        self.accept_disp = kaa.notifier.SocketDispatcher(self.accept)
        self.accept_disp.register(self.socket)


    def accept(self):
        """
        Callback for new connections.
        """
        s, addr = self.socket.accept()
        if hasattr(s, 'setblocking'):
            s.setblocking(1)
        request = cherrypy._cpwsgiserver.HTTPRequest(s, addr, self)
        self.requests.put(request)
        return True


    def stop(self):
        """
        Stop the server.
        """
        self.accept_disp.unregister()
        cherrypy._cpwsgi.WSGIServer.stop(self)


class Server(cherrypy._cpserver.Server):
    """
    Wrapper for the base CherryPy Server using the WSGIServer. Most of this
    code is copied from cherrypy._cpserver.Server.start_http_server. The only
    difference is that there is no thread used to start the WSGIServer.
    """
    def start_http_server(self, blocking=True):
        """
        Start the requested HTTP server.
        """
        if self.httpserver is not None:
            msg = ("You seem to have an HTTP server still running."
                   "Please call server.stop_http_server() "
                   "before continuing.")
            warnings.warn(msg)

        if self.httpserverclass is None:
            return

        if cherrypy.config.get('server.socketPort'):
            host = cherrypy.config.get('server.socketHost')
            port = cherrypy.config.get('server.socketPort')

            cherrypy._cpserver.wait_for_free_port(host, port)

            if not host:
                host = 'localhost'
            onWhat = "http://%s:%s/" % (host, port)
        else:
            onWhat = "socket file: %s" % cherrypy.config.get('server.socketFile')

        # Instantiate the server.
        self.httpserver = self.httpserverclass()

        self.httpserver.start()
        cherrypy.log("11 Serving HTTP on %s" % onWhat, 'HTTP')


def start(Root, *args, **kwargs):
    """
    Setup CherryPy and start the server. On application shutdown, the server
    will be stopped correctly, no need to call cherrypy.server.stop().
    """
    cherrypy.root = Root(*args, **kwargs)
    cherrypy.config.update( {
        'autoreload.on': False,
        'server.logToScreen': config.debug,
        'logDebugInfoFilter.on': config.debug,
        'server.socketPort': config.port })
    cherrypy.server = Server()
    cherrypy.server.start(True, WSGIServer)
    kaa.notifier.signals['shutdown'].connect(cherrypy.server.stop)
