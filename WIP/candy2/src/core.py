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

__all__ = [ 'is_template', 'Color', 'Font', 'Properties', 'threaded', 'Lock' ]

# python imports
import logging
import sys
import threading
import gobject

# kaa imports
import kaa

# get logging object
log = logging.getLogger('kaa.candy')


def is_template(obj):
    """
    Returns True if the given object is a kaa.candy template class. This function
    is needed to check if a given widget is a real clutter widget or only a template
    for creating one.
    """
    return getattr(obj, '__is_template__', False)


class Color(list):
    """
    Color object which is a list of r,g,b,a with values between 0 and 255.
    """
    def __init__(self, *col):
        """
        Create a new color object. All C{set_color} member functions of kaa.candy
        widgets use this class for setting a color and not the clutter color object.
        The Color object is list of r,g,b,a with values between 0 and 255.

        @param col: one of the following types
         - a tuple r,g,b,a
         - a clutter color object
         - a string #aarrggbb
        """
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
        Convert to list used by cairo.
        @returns: list with float values from 0 to 1.0
        """
        return [ x / 255.0 for x in self ]


class Font(object):
    """
    Font object containing font name and font size
    @ivar name: font name
    @ivar size: font size
    """
    def __init__(self, name):
        """
        Create a new font object
        @param name: name and size of the font, e.g. Vera:24
        """
        self.name, size = name.split(':')
        self.size = int(size)


class Properties(dict):
    """
    Properties class to apply the given properties to a widget. This is a
    dictionary for clutter functions to call after the widget is created.
    It is used by candyxml and the animation submodule.
    """

    #: candyxml name
    candyxml_name = 'properties'

    def apply(self, widget):
        """
        Apply to the given widget.
        @param widget: a kaa.candy.Widget
        """
        for func, value in self.items():
            getattr(widget, 'set_' + func)(*value)
            if func == 'anchor_point':
                widget.move_by(*value)

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the candyxml element and create a Properties object::

          <widget_or_animation>
            <properties key=value key=value>
          </widget_or_animation>

        Possible keys are C{opacity} (int), C{depth} (int),
        C{scale} (float,float), C{anchor_point} (float,float)
        """
        properties = cls()
        for key, value in element.attributes():
            if key in ('opacity', 'depth'):
                value = [ int(value) ]
            elif key in ('scale','anchor_point'):
                value = [ float(x) for x in value.split(',') ]
                if key in ('scale','anchor_point'):
                    value = int(value[0] * element.get_scale_factor()[0]), \
                            int(value[1] * element.get_scale_factor()[1])
            else:
                value = [ value ]
            properties[key] = value
        return properties


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
        Lock the clutter thread.
        @param auto_release: if True, the lock will be released on the next
            iteration of the kaa mainloop by itself.
        @returns: None
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
        Release the lock. The clutter thread will still be locked if another
        Lock instance is holding a lock.
        @returns: None
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


def threaded():
    """
    Decorator to force the execution of the function in the clutter mainloop
    and blocking the mainloop during that time. This decorator should be
    used for function that create or manipulate kaa.candy widgets. Since the
    kaa mainloop will be blocked during execution to avoid race conditions
    decorated functions should be very small and can not wait for additional
    input from the mainloop.
    """

    def decorator(func):
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

        if 'epydoc' in sys.modules:
            return func
        newfunc.func_name = func.func_name
        return newfunc

    return decorator
