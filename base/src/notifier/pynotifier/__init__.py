#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# __init__.py
#
# Author: Andreas Büsching <crunchy@bitkipper.net>
#
# package initialisation
#
# $Id: __init__.py 82 2006-06-14 22:35:47Z crunchy $
#
# Copyright (C) 2004, 2005, 2006 Andreas Büsching <crunchy@bitkipper.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Simple mainloop that watches sockets and timers."""

from version import *

from select import select
from time import time

import log

socket_add = None
socket_remove = None

timer_add = None
timer_remove = None

dispatcher_add = None
dispatcher_remove = None

loop = None
step = None

in_use = None

# notifier types
( GENERIC, QT, GTK, WX ) = range( 4 )

# socket conditions
IO_READ = None
IO_WRITE = None
IO_EXCEPT = None

def init( type = GENERIC ):
    global timer_add
    global socket_add
    global dispatcher_add
    global timer_remove
    global socket_remove
    global dispatcher_remove
    global loop, step
    global IO_READ, IO_WRITE, IO_EXCEPT

    if type == GENERIC:
        import nf_generic as nf_impl
    elif type == QT:
        import nf_qt as nf_impl
    elif type == GTK:
        import nf_gtk as nf_impl
    elif type == WX:
        import nf_wx as nf_impl
	log.warn( 'the WX notifier is deprecated and is no longer maintained' )
    else:
        raise Exception( 'unknown notifier type' )

    socket_add = nf_impl.socket_add
    socket_remove = nf_impl.socket_remove
    timer_add = nf_impl.timer_add
    timer_remove = nf_impl.timer_remove
    dispatcher_add = nf_impl.dispatcher_add
    dispatcher_remove = nf_impl.dispatcher_remove
    loop = nf_impl.loop
    step = nf_impl.step
    IO_READ = nf_impl.IO_READ
    IO_WRITE = nf_impl.IO_WRITE
    IO_EXCEPT = nf_impl.IO_EXCEPT

class Callback:
    def __init__( self, function, *args ):
        self._function = function
        self._args = args

    def __call__( self, *args ):
        tmp = list( args )
        if self._args:
            tmp.extend( self._args )
        if tmp:
            return self._function( *tmp )
        else:
            return self._function()

    def __cmp__( self, rvalue ):
        if not callable( rvalue ): return -1

        if ( isinstance( rvalue, Callback ) and \
               self._function == rvalue._function ) or \
               self._function == rvalue:
            return 0

        return -1

    def __nonzero__( self ):
        return bool( self._function )

    def __hash__( self ):
        return self._function.__hash__()
