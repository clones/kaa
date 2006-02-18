# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__.py - interface to kaa.vfs
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-vfs - A virtual filesystem with metadata
# Copyright (C) 2005 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file AUTHORS for a complete list of authors.
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

__all__ = [ 'connect' ]

import os
import popen2
import time
import socket
import logging

from kaa.notifier import step, Timer

from client import Client

# get logging object
log = logging.getLogger('vfs')

def connect(vfsdb, logfile=None, loglevel=logging.INFO):
    """
    Connect to the vfs database dir given by 'vfsdb'. A server will be started
    if no server is running. The new server will print debug output to the
    given logfile. If a server is already running, logfile has no effect. If
    a loglevel is given and the server will be started, it will use the given
    loglevel. If no logfile is given, the server will log to vfsdb/log.
    The server can be used by different clients in different applications if
    the are started by the same user. It will shutdown if no client is connected
    for over 5 seconds.
    """
    try:
        # try to connect to an already running server
        return Client(vfsdb)
    except socket.error:
        pass

    # check logfile
    if not logfile:
        logfile = os.path.join(vfsdb, 'log')
    # start server
    server = os.path.join(os.path.dirname(__file__), 'server.py')
    server_fd = popen2.popen3(['python', '-OO', server, logfile, str(loglevel)])

    # wait for server to start
    # use a small timer to make sure step() comes back
    stop = time.time() + 2
    t = Timer(lambda x: True, 1)
    t.start(0.01)
    while time.time() < stop:
        step()
        try:
            c = Client(vfsdb)
            # client ready, close fd to server
            for fd in server_fd:
                fd.close()
            # stop temp timer
            t.stop()
            return c
        except socket.error:
            pass

    # no server found, print debug
    for fd in server_fd:
        try:
            for msg in fd.readlines():
                log.error(msg[:-1])
        except IOError:
            pass
        fd.close()
    # stop temp timer
    t.stop()

    # raise error
    raise OSError('Unable to start vfs server')
