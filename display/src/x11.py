# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# x11.py - X11 Display classes
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.display - Generic Display Module
# Copyright (C) 2005-2008 Dirk Meyer, Jason Tackaberry
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
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

# python imports
import weakref
import struct
import logging
import traceback

# kaa for the socket callback
import kaa
from kaa.utils import property

# the display module
import _X11

# get logging object
log = logging.getLogger('display.x11')

# default X11 display
_default_x11_display = None

_keysym_names = {
    338: "up",
    340: "down",
    337: "left",
    339: "right",

    446: "F1",
    447: "F2",
    448: "F3",
    449: "F4",
    450: "F5",
    451: "F6",
    452: "F7",
    453: "F8",
    454: "F9",
    455: "F10",
    456: "F11",
    457: "F21",

    355: "ins",
    511: "del",
    336: "home",
    343: "end",
    283: "esc",
    269: "enter",
    264: "backspace",
    32: "space",

    489: "left-alt",
    490: "right-alt",
    483: "left-ctrl",
    484: "right-ctrl",
    481: "left-shift",
    482: "right-shift",
    359: "menu",
    275: "pause",

    # keypad
    427: "kp_plus",
    429: "kp_minus"
}

class X11Error(Exception):
    def __init__(self, serial, error_code, request_code, minor_code, msg):
        super(X11Error, self).__init__(serial, error_code, request_code, minor_code, msg)
        self.serial = serial
        self.error_code = error_code
        self.request_code = request_code
        self.minor_code = minor_code
        self.strerror = msg

    def __str__(self):
        return '[X11 Error %d]: %s' % (self.error_code, self.strerror)


class X11Display(kaa.Object):

    XEVENT_MOTION_NOTIFY = 6
    XEVENT_EXPOSE = 12
    XEVENT_BUTTON_PRESS = 4
    XEVENT_BUTTON_RELEASE = 5
    XEVENT_KEY_PRESS = 2
    XEVENT_KEY_RELEASE = 3
    XEVENT_FOCUS_IN = 9
    XEVENT_FOCUS_OUT = 10
    XEVENT_EXPOSE = 12
    XEVENT_UNMAP_NOTIFY = 18
    XEVENT_MAP_NOTIFY = 19
    XEVENT_CONFIGURE_NOTIFY = 22
    XEVENT_CLIENT_MESSAGE = 33

    __kaasignals__ = {
        'error':
            '''
            Emits when an untrapped X error occurs.

            .. describe:: def callback(x11error, ...)

               :param x11error: an instance of an X11Error exception
            '''
    }

    def __init__(self, dispname = ""):
        super(X11Display, self).__init__()
        self._display = _X11.X11Display(dispname, X11Error, kaa.WeakCallable(self._handle_error))
        self._windows = {}

        dispatcher = kaa.WeakIOMonitor(self.handle_events)
        dispatcher.register(self.socket)
        # Also connect to the step signal. It is a bad hack, but when
        # drawing is done, the socket is read and we will miss keypress
        # events when doing drawings.
        kaa.main.signals['step'].connect_weak(self.handle_events)

    def _handle_error(self, exc):
        if len(self.signals['error']) == 0:
            # No callbacks connected to handle errors, so just dump the error
            # to stdout.  Shave off the last 3 stack frames since they're
            # involved in getting us to this error handler and not of interest
            # to the user.
            stack = ''.join(traceback.format_stack()[:-3])
            if isinstance(exc, X11Error):
                log.error('An untrapped X error was received: %s (serial=%ld error=%d request=%d minor=%d)',
                          exc.strerror, exc.serial, exc.error_code, exc.request_code, exc.minor_code)
            else:
                log.error('An untrapped X error was received: %s', exc)
            log.error('A stack follows, but note that errors may be asynchronous:\n%s', stack)
        else:
            self.signals['error'].emit(exc)


    def handle_events(self):
        window_events = {}
        for event, data in self._display.handle_events():
            wid = 0
            if event in X11Display.XEVENT_WINDOW_EVENTS:
                wid = data["window"]

            # Create event dict for windows we know about.  It's possible we
            # may receive events for windows we don't know about (i.e. not
            # in self._windows); these are children of managed windows and
            # these events can be ignored.
            if wid and wid in self._windows:
                if wid not in window_events:
                    window_events[wid] = []
                if event == X11Display.XEVENT_CONFIGURE_NOTIFY:
                    # Remove any existing configure events in the list (only
                    # the last one applies)
                    window_events[wid] = [ x for x in window_events[wid] if x[0] !=
                                           X11Display.XEVENT_CONFIGURE_NOTIFY ]
                window_events[wid].append((event, data))

        for wid, events in window_events.items():
            window = self._windows[wid]()
            if not window:
                # Window no longer exists.
                del self._windows[wid]
            else:
                window.handle_events(events)

        # call the socket again
        return True


    def __getattr__(self, attr):
        if attr in ("socket", "composite_redirect"):
            return getattr(self._display, attr)

        return getattr(super(X11Display, self), attr)

    def sync(self):
        return self._display.sync()

    def lock(self):
        return self._display.lock()

    def unlock(self):
        return self._display.unlock()

    def get_size(self, screen = -1):
        return self._display.get_size(screen)

    def get_string(self):
        return self._display.get_string()

    def glx_supported(self):
        return self._display.glx_supported()

    def composite_supported(self):
        return self._display.composite_supported()

    def get_root_window(self):
        return X11Window(window = self._display.get_root_id())


X11Display.XEVENT_WINDOW_EVENTS_LIST = filter(lambda x: x.find("XEVENT_") != -1, dir(X11Display))
X11Display.XEVENT_WINDOW_EVENTS = map(lambda x: getattr(X11Display, x), X11Display.XEVENT_WINDOW_EVENTS_LIST)

def _get_display(display):
    if not display:
        global _default_x11_display
        if not _default_x11_display:
            _default_x11_display = X11Display()
        display = _default_x11_display

    if isinstance(display, basestring):
        # display provided is a name, so create X11Display based on that
        display = X11Display(display)

    assert(type(display) == X11Display)
    return display



class X11Window(object):
    def __init__(self, display = None, window = None, **kwargs):
        """
        Create a new X11 window or wrap an existing X11 window.  If display is
        None, it will use the default display (based on the DISPLAY environment
        variable).  If window is a numeric, it will consider it a window id and
        can be used to wrap an existing X11 window.  The window parameter may
        also be a lower level _X11.X11Window object.

        If window is none, then a new window will be created, and the
        following kwargs apply:
           size: 2-tuple of width and height for the window (required)
           title: A string representing the window's title (optional)
           parent: An existing X11Window object of which the new window will
                   be a subwindow.
        """
        display = _get_display(display)
        if window:
            if isinstance(window, (long, int)):
                # Create new X11Window object based on existing window id.
                self._window = _X11.X11Window(display._display, (-1, -1), window = long(window))
            elif isinstance(window, _X11.X11Window):
                self._window = window
            else:
                raise ValueError, "window parameter must be an integer."
        else:
            if "title" in kwargs:
                assert(type(kwargs["title"]) == str)
            if "parent" in kwargs:
                assert(isinstance(kwargs["parent"], X11Window))
                kwargs["parent"] = kwargs["parent"]._window

            w, h = kwargs.get('size', (1, 1))
            self._window = _X11.X11Window(display._display, (w or 1, h or 1), **kwargs)

        self._display = display
        display._windows[self._window.wid] = weakref.ref(self)
        self._cursor_hide_timeout = 1
        self._cursor_hide_timer = kaa.WeakOneShotTimer(self._cursor_hide_cb)
        self._cursor_visible = True
        self._fs_size_save = None
        self._last_configured_size = 0, 0

        self.signals = kaa.Signals(
            "key_press_event",     # key pressed
            "key_release_event",   # key release
            "button_press_event",  # Button pressed
            "button_release_event",# Button released
            "focus_in_event",      # window gets focus
            "focus_out_event",     # window looses focus
            "expose_event",        # expose event
            "map_event",           # shown/mapped on to the screen
            "unmap_event",         # hidden/unmapped from the screen
            "resize_event",        # window resized
            "delete_event",
            "configure_event")     # ?

    def __str__(self):
        return '<X11Window object id=0x%x>' % self._window.wid

    def get_display(self):
        return self._display

    def raise_(self):
        self._window.raise_()
        self._display.handle_events()

    def lower(self):
        self._window.lower()
        self._display.handle_events()

    def lower_window():
        'Deprecated: do not use in new code; use lower() instead.'
        return self.lower()

    def raise_window():
        'Deprecated: do not use in new code; use raise_() instead.'
        return self.raise_()

    def show(self, raised = False):
        self._window.show(raised)
        self._display.handle_events()

    def hide(self):
        self._window.hide()
        self._display.handle_events()

    def set_visible(self, visible = True):
        if visible:
            self.show()
        else:
            self.hide()

    def get_visible(self):
        return self._window.get_visible() != 0

    def render_imlib2_image(self, i, dst_pos = (0, 0), src_pos = (0, 0),
                            size = (-1, -1), dither = True, blend = False):
        return _X11.render_imlib2_image(self._window, i._image, dst_pos, \
                                            src_pos, size, dither, blend)

    def handle_events(self, events):
        expose_regions = []
        for event, data in events:
            if event == X11Display.XEVENT_MOTION_NOTIFY:
                # Mouse moved, so show cursor.
                if not self._cursor_visible:
                    if self._cursor_hide_timeout != 0:
                            self.set_cursor_visible(True)
                    self._cursor_hide_timer.start(self._cursor_hide_timeout)

            elif event == X11Display.XEVENT_BUTTON_PRESS:
                 self.signals["button_press_event"].emit(data["pos"], data["state"], data["button"])

            elif event == X11Display.XEVENT_BUTTON_RELEASE:
                 self.signals["button_release_event"].emit(data["pos"], data["state"], data["button"])
            
            elif event in (X11Display.XEVENT_KEY_PRESS, X11Display.XEVENT_KEY_RELEASE):
                key = data["key"]
                if key in _keysym_names:
                    key = _keysym_names[key]
                elif key < 255:
                    key = chr(key)
                if event == X11Display.XEVENT_KEY_PRESS:
                    self.signals["key_press_event"].emit(key)
                else:
                    self.signals["key_release_event"].emit(key)

            elif event == X11Display.XEVENT_EXPOSE:
                # Queue expose regions so we only need to emit one signal.
                expose_regions.append((data["pos"], data["size"]))

            elif event == X11Display.XEVENT_MAP_NOTIFY:
                self.signals["map_event"].emit()

            elif event == X11Display.XEVENT_UNMAP_NOTIFY:
                self.signals["unmap_event"].emit()

            elif event == X11Display.XEVENT_CONFIGURE_NOTIFY:
                cur_size = self.get_size()
                last_size = self._last_configured_size
                if last_size != cur_size and last_size != (-1, -1):
                    # Set this now to prevent reentry.
                    self._last_configured_size = -1, -1
                    self.signals["resize_event"].emit(last_size, cur_size)
                    # Callback could change size again, so save our actual
                    # size to prevent being called again.
                    self._last_configured_size = self.get_size()
                self.signals["configure_event"].emit(data["pos"], data["size"])
            elif event == X11Display.XEVENT_FOCUS_IN:
                self.signals["focus_in_event"].emit()
            elif event == X11Display.XEVENT_FOCUS_OUT:
                self.signals["focus_out_event"].emit()
            elif event == X11Display.XEVENT_CLIENT_MESSAGE:
                if data['type'] == 'delete':
                    if len(self.signals['delete_event']) == 0:
                        # Default action on a delete event: just unmap it.
                        self.hide()
                    else:
                        self.signals['delete_event'].emit()


        if len(expose_regions) > 0:
            self.signals["expose_event"].emit(expose_regions)


    def move(self, x, y=None, force=False):
        if y is None:
            log.warning('X11Window.move() now takes 2 arguments instead of 1 tuple')
            x, y = x
        return self.set_geometry((x, y), (-1, -1), force=force)

    def resize(self, width, height=None, force=False):
        if height is None:
            log.warning('X11Window.resize() now takes 2 arguments instead of 1 tuple')
            width, height = width
        return self.set_geometry((-1, -1), (width, height), force)

    def set_geometry(self, pos, size, force = False):
        if self.get_fullscreen() and not force:
            self._fs_size_save = size
            return False

        w, h = size
        self._window.set_geometry(pos, (w or 1, h or 1))
        self._display.handle_events()
        return True

    def get_geometry(self, absolute = False):
        """
        Returns 2-tuple of position and size (x, y), (width, height)
        of the window.  If absolute is False (default), (x, y) are relative
        to the window's parent.  If absolute is True, coordinates are
        relative to the root window.
        """
        return self._window.get_geometry(absolute)

    def get_parent(self):
        """
        Returns the parent of the window.  If no parent exists (i.e. root window)
        None is returned.
        """
        wid = self._window.get_parent()
        if wid:
            return X11Window(window = self._window.get_parent())

    def get_size(self):
        return self.get_geometry()[1]

    def get_pos(self, absolute = False):
        return self.get_geometry(absolute)[0]

    def set_cursor_visible(self, visible):
        self._window.set_cursor_visible(visible)
        self._cursor_visible = visible
        self._display.handle_events()

    def _cursor_hide_cb(self):
        self.set_cursor_visible(False)

    def set_cursor_hide_timeout(self, timeout):
        self._cursor_hide_timeout = timeout
        self._cursor_hide_timer.start(self._cursor_hide_timeout)

    def set_fullscreen(self, fs = True):
        if not fs:
            if self._fs_size_save:
                self.resize(*self._fs_size_save, force=True)
                self._window.set_fullscreen(False)
                self._fs_size_save = None
                return True

            return False

        if self._fs_size_save:
            return False

        self._fs_size_save = self.get_size()
        display_size = self.get_display().get_size()
        self._window.set_fullscreen(True)
        self.resize(*display_size, force=True)

    def get_fullscreen(self):
        return self._fs_size_save != None

    def set_transient_for(self, window=None, transient=True):
        win_id = 0
        if window:
            win_id = window.id
        return self._window.set_transient_for(win_id, transient)

    def get_id(self):
        log.warning('Window.get_id() is deprecated in favor of Windows.id property')
        return self._window.wid

    @property
    def id(self):
        return self._window.wid

    @property
    def owner(self):
        """
        True if the X11Window python object owns the underlying X11 Window
        construct.   If True, the window will be destroyed when the python
        wrapper object is deallocated.
        """
        return self._window.owner

    @owner.setter
    def owner(self, value):
        self._window.owner = value

    def focus(self):
        return self._window.focus()

    def set_title(self, title):
        return self._window.set_title(title)

    def get_title(self):
        return self._window.get_title()

    def get_children(self, recursive = False, visible_only = False, titled_only = False):
        """
        Returns all child windows as X11Window objects.  If recursive is True,
        all descendants will be returned.  If visible_only is True, only those
        children which are visible are included (unmapped children or mapped 
        children that are offscreen are not included).  If titled_only is True,
        only those windows with titles set will be included.
        """
        return [ X11Window(window = wid) for wid in self._window.get_children(recursive, visible_only, titled_only) ]

    def get_properties(self):
        """
        Returns a dictionary of X properties associated with this window.
        Properties are converted to the appropriate python type, although if
        the given property type is not supported, the value for that property
        will be a 4-tuple of (type, format, n_items, data) where type is a
        string representing the type of the atom, format is 8 for character,
        16 for short, and 32 for int, n_items is the number of items of the
        given format in the data buffer.
        """
        props = {}
        for (name, type, format, n_items, data) in self._window.get_properties():
            struct_format = {
                'INTEGER': 'i',
                'CARDINAL': 'L',
                'WINDOW': 'L',
                'STRING': 's',
                'UTF8_STRING': 's'
            }.get(type, None)

            if struct_format:
                struct_format = '%d%s' % (n_items, struct_format)
                buflen = struct.calcsize(struct_format)
                data = struct.unpack(struct_format, data[:buflen])
                if len(data) == 1:
                    data = data[0]
                if type in ('STRING', 'UTF8_STRING'):
                    data = data.strip('\x00').split('\x00')
                    if type == 'UTF8_STRING':
                        data = [ x.decode('utf-8') for x in data]
                    if len(data) == 1:
                        data = data[0]
            else:
                # Unsupported type, we just pass the raw buffer back to the user.
                pass

            props[name] = data

        return props

    def set_shape_mask(self, mask, pos, size ):
        """
        Set the shape mask for a window using the XShape extension.
        
        @param mask: A string containing either a bitmask or a byte-per-pixel 
                     to use as the shape mask.
        @param pos: X,Y Position in the window to apply the mask.
        @param size: Width,Height of the mask.
        """
        
        if len(mask) == ((size[0] * size[1]) + 7) / 8 or len(mask) == size[0] * size[1]:
            # Add 7 ensures that when we divided by 8 we have enough bytes to store 
            # all the bits needed. Take 3w * 3h = 9 bits, (3 * 3) + 7 = 16 bits 
            # ie 2 bytes.
            self._window.set_shape_mask(mask, pos, size)
        else:
            raise ValueError('Mask is wrong length!')
    
    def set_shape_mask_from_imlib2_image(self, image, pos=(0,0), threshold=128):
        """
        Set the shape mask for the window based on the pixel alpha values.
        
        @param image: Imlib2 image with per pixel alpha to use as the mask.
        @param pos: X,Y Position in the window to apply the mask.
        @param threshold: Pixels with alpha values >= to this will be shown.
        """
        if image.has_alpha:
           _X11.set_shape_mask_from_imlib2_image(self._window, image._image, pos, threshold)
        else:
            raise ValueError('Image does not have an alpha channel!')
        
    def reset_shape_mask(self):
        """
        Reset (remove) the shape mask of the window.
        """
        self._window.reset_shape_mask()
    
    def set_decorated(self, setting):
        """
        Set whether the window manager should add a border and controls to the
        window or not.
        
        Note: Windows must be hidden or not yet shown before changing this setting.
        
        @param setting: True if the window should be decorated, false if not.
        """
        self._window.set_decorated(setting)

    def draw_rectangle(self, pos, size, color):
        if isinstance(color, basestring) and color[0] == '#' and len(color) == 7:
            color = int(color[1:3], 16), int(color[3:5], 16), int(color[5:], 16)
        self._window.draw_rectangle(pos, size, color)
