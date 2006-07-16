#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: Andreas Büsching <crunchy@bitkipper.net>
#
# notifier wrapper for GTK+ 2.x
#
# $Id: nf_gtk.py 95 2006-07-16 17:52:36Z crunchy $
#
# Copyright (C) 2004, 2005, 2006
#      	Andreas Büsching <crunchy@bitkipper.net>
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

"""Simple mainloop that watches sockets and timers."""

import gobject
import gtk

import dispatch
import log

IO_READ = gobject.IO_IN
IO_WRITE = gobject.IO_OUT
IO_EXCEPT = gobject.IO_ERR

# map of Sockets/Methods -> GTK source IDs
_gtk_socketIDs = {}
_gtk_socketIDs[ IO_READ ] = {}
_gtk_socketIDs[ IO_WRITE ] = {}

def socket_add( socket, method, condition = IO_READ ):
    """The first argument specifies a socket, the second argument has to be a
    function that is called whenever there is data ready in the socket."""
    global _gtk_socketIDs
    source = gobject.io_add_watch( socket, condition,
                                   _socket_callback, method )
    _gtk_socketIDs[ condition ][ socket ] = source

def _socket_callback( source, condition, method ):
    """This is an internal callback function, that maps the GTK source IDs
    to the socket objects that are used by pynotifier as an identifier
    """
    global _gtk_socketIDs
    if _gtk_socketIDs[ condition ].has_key( source ):
        ret = method( source )
        if not ret:
	    socket_remove( source, condition )
	return ret

    log.info( "socket '%s' not found" % source )
    return False

def socket_remove( socket, condition = IO_READ ):
    """Removes the given socket from scheduler."""
    global _gtk_socketIDs
    if _gtk_socketIDs[ condition ].has_key( socket ):
	gobject.source_remove( _gtk_socketIDs[ condition ][ socket ] )
	del _gtk_socketIDs[ condition ][ socket ]
    else:
	log.info( "socket '%s' not found" % socket )

def timer_add( interval, method ):
    """The first argument specifies an interval in milliseconds, the
    second argument a function. This is function is called after
    interval seconds. If it returns true it's called again after
    interval seconds, otherwise it is removed from the scheduler. The
    third (optional) argument is a parameter given to the called
    function."""
    return gobject.timeout_add( interval, method )

def timer_remove( id ):
    """Removes the timer specified by id from the scheduler."""
    gobject.source_remove( id )

dispatcher_add = dispatch.dispatcher_add
dispatcher_remove = dispatch.dispatcher_remove

def step( sleep = True, external = True ):
    gtk.main_iteration_do( block = sleep )
    if external:
        dispatch.dispatcher_run()

def loop():
    """Execute main loop forver."""
    while 1:
        step()

def _init():
    gobject.threads_init()
