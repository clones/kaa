# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - Helper classes and decorator
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008 Dirk Meyer, Jason Tackaberry
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

__all__ = [ 'Color', 'Font', 'threaded', 'Lock' ]

# python imports
import logging
import sys
import threading
import gobject

# kaa imports
import kaa

# get logging object
log = logging.getLogger('kaa.candy')


class Color(list):
    """
    Color object.
    """
    def __init__(self, *col):
        if len(col) > 1:
            return super(Color, self).__init__(col)
        # Convert a 32-bit (A)RGB color
        if col == None:
            return super(Color, self).__init__((0,0,0,255))
        if hasattr(col[0], 'red'):
            # clutter.Color object
            return super(Color, self).__init__((
                col[0].red, col[0].green, col[0].blue, col[0].alpha))
        # convert 0x???????? string
        col = long(col[0], 16)
        a = 255 - ((col >> 24) & 0xff)
        r = (col >> 16) & 0xff
        g = (col >> 8) & 0xff
        b = (col >> 0) & 0xff
        super(Color, self).__init__((r,g,b,a))

    def to_cairo(self):
        """
        Convert to list used by cairo (float values from 0-1)
        """
        return [ x / 255.0 for x in self ]

class Font(object):
    """
    Font object
    """
    def __init__(self, name):
        self.name, size = name.split(':')
        self.size = int(size)


#: thread the clutter mainloop is running in
gobject_thread = None

def gobject_execute(callback):
    """
    Execute the callback in the gobject thread.
    """
    try:
        callback.exception = None
        callback.result = callback()
    except Exception, e:
        callback.exception = sys.exc_info()
        log.exception('threaded')
    finally:
        callback.event.set()


def set_gobject_thread(dummy):
    """
    Set the current thread as gobject_thread.
    """
    global gobject_thread
    gobject_thread = threading.currentThread()


class Lock(object):
    """
    Class to lock the clutter thread. While a lock is active the gobject
    mainloop will block in idle_add executing all threaded callbacks
    without redrawing. You can use the acquire() and release() functions.
    """
    instance = None
    counter = 0
    _locked = False

    def acquire(self, auto_release=True):
        """
        Lock the clutter thread. If auto_release is True, the lock will be
        released on the next iteration of the kaa mainloop by itself.
        """
        Lock.counter += 1
        if auto_release:
            kaa.signals['step'].connect_once(self.release)
        self._locked = True
        if Lock.instance:
            return self
        self._gobject_event = threading.Event()
        self._callbacks = []
        self._stopping = False
        self._main_event = threading.Event()
        Lock.instance = self
        gobject.idle_add(self._gobject_callback, None)
        return self

    def release(self):
        """
        Release the clutter thread.
        """
        if not self._locked:
            return
        self._locked = False
        Lock.counter -= 1
        if Lock.counter:
            return
        Lock.instance._stopping = True
        Lock.instance._gobject_event.set()
        Lock.instance._main_event.wait()
        Lock.instance = None

    def _gobject_callback(self, arg=None):
        """
        GObject loop handler.
        """
        while not self._stopping:
            self._gobject_event.wait()
            while self._callbacks:
                gobject_execute(self._callbacks.pop(0))
        self._main_event.set()


class threaded(object):
    """
    Decorator to force the execution of the function in the clutter mainloop
    and _blocking_ the mainloop during that time.
    """

    def __call__(self, func):
        """
        Decorator function.
        """
        def newfunc(*args, **kwargs):
            if gobject_thread == threading.currentThread():
                return func(*args, **kwargs)
            if gobject_thread is None:
                gobject.idle_add(set_gobject_thread, None)
            callback = kaa.Callback(func, *args, **kwargs)
            callback.event = threading.Event()
            if Lock.instance:
                Lock.instance._callbacks.append(callback)
                Lock.instance._gobject_event.set()
            else:
                gobject.idle_add(gobject_execute, callback)
            callback.event.wait()
            if callback.exception:
                exc_type, exc_value, exc_tb_or_stack = callback.exception
                raise exc_type, exc_value, exc_tb_or_stack
            return callback.result
        newfunc.func_name = func.func_name
        return newfunc
