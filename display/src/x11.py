# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# x11.py - X11 Display classes
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.display - Generic Display Module
# Copyright (C) 2005-2006 Dirk Meyer, Jason Tackaberry
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

# kaa notifier for the socket callback
import kaa.notifier
from kaa.notifier import Signals

# the display module
import _X11

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

class X11Display(object):

    XEVENT_MOTION_NOTIFY = 6
    XEVENT_EXPOSE = 12
    XEVENT_BUTTON_PRESS = 4
    XEVENT_KEY_PRESS = 2
    XEVENT_FOCUS_IN = 9
    XEVENT_FOCUS_OUT = 10
    XEVENT_EXPOSE = 12
    XEVENT_UNMAP_NOTIFY = 18
    XEVENT_MAP_NOTIFY = 19
    XEVENT_CONFIGURE_NOTIFY = 22

    #XEVENT_WINDOW_EVENTS = (6, 12, 4, 2, 22, 18, 19)

    def __init__(self, dispname = ""):
        self._display = _X11.X11Display(dispname)
        self._windows = {}

        dispatcher = kaa.notifier.WeakSocketDispatcher(self.handle_events)
        dispatcher.register(self.socket)
        # Also connect to the step signal. It is a bad hack, but when
        # drawing is done, the socket is read and we will miss keypress
        # events when doing drawings.
        kaa.notifier.signals['step'].connect_weak(self.handle_events)

    def handle_events(self):
        window_events = {}
        for event, data in self._display.handle_events():
            wid = 0
            if event in X11Display.XEVENT_WINDOW_EVENTS:
                wid = data["window"]
            if wid:
                if wid not in window_events:
                    window_events[wid] = []
                if event == X11Display.XEVENT_CONFIGURE_NOTIFY:
                    # Remove any existing configure events in the list (only
                    # the last one applies)
                    window_events[wid] = [ x for x in window_events[wid] if x[0] !=
                                           X11Display.XEVENT_CONFIGURE_NOTIFY ]
                window_events[wid].append((event, data))

        for wid, events in window_events.items():
            assert(wid in self._windows)
            window = self._windows[wid]()
            if not window:
                # Window no longer exists.
                del self._windows[wid]
            else:
                window.handle_events(events)

        # call the socket again
        return True


    def __getattr__(self, attr):
        if attr in ("socket,"):
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



X11Display.XEVENT_WINDOW_EVENTS_LIST = filter(lambda x: x.find("XEVENT_") != -1, dir(X11Display))
X11Display.XEVENT_WINDOW_EVENTS = map(lambda x: getattr(X11Display, x), X11Display.XEVENT_WINDOW_EVENTS_LIST)

def _get_display(display):
    if not display:
        global _default_x11_display
        if not _default_x11_display:
            _default_x11_display = X11Display()
        display = _default_x11_display

    assert(type(display) == X11Display)
    return display



class X11Window(object):
    def __init__(self, display = None, window = None, **kwargs):
        display = _get_display(display)
        if window:
            self._window = window
        else:
            assert("size" in kwargs)
            if "title" in kwargs:
                assert(type(kwargs["title"]) == str)
            if "parent" in kwargs:
                assert(isinstance(kwargs["parent"], X11Window))
                kwargs["parent"] = kwargs["parent"]._window

            self._window = _X11.X11Window(display._display, kwargs["size"], **kwargs)

        self._display = display
        display._windows[self._window.ptr] = weakref.ref(self)
        self._cursor_hide_timeout = -1
        self._cursor_hide_timer = kaa.notifier.WeakOneShotTimer(self._cursor_hide_cb)
        self._cursor_visible = True
        self._fs_size_save = None
        self._last_configured_size = 0, 0

        self.signals = Signals(
            "key_press_event", # key pressed
            "focus_in_event",  # window gets focus
            "focus_out_event", # window looses focus
            "expose_event",    # expose event
            "map_event",       # ?
            "unmap_event",     # ?
            "resize_event",    # window resized
            "configure_event") # ?

    def get_display(self):
        return self._display

    def raise_window(self):
        self._window.raise_window()
        self._display.handle_events()

    def lower_window(self):
        self._window.lower_window()
        self._display.handle_events()

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
        return self._window.get_visible()

    def render_imlib2_image(self, i, dst_pos = (0, 0), src_pos = (0, 0),
                            size = (-1, -1), dither = True, blend = False):
        return _X11.render_imlib2_image(self._window, i._image, dst_pos, \
                                            src_pos, size, dither, blend)

    def handle_events(self, events):
        expose_regions = []
        for event, data in events:
            if event == X11Display.XEVENT_MOTION_NOTIFY:
                # Mouse moved, so show cursor.
                if self._cursor_hide_timeout != 0 and not self._cursor_visible:
                    self.set_cursor_visible(True)

                self._cursor_hide_timer.start(self._cursor_hide_timeout)

            elif event == X11Display.XEVENT_KEY_PRESS:
                key = data["key"]
                if key in _keysym_names:
                    key = _keysym_names[key]
                elif key < 255:
                    key = chr(key)
                self.signals["key_press_event"].emit(key)

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


        if len(expose_regions) > 0:
            self.signals["expose_event"].emit(expose_regions)


    def move(self, pos, force = False):
        return self.set_geometry(pos, (-1, -1))

    def resize(self, size, force = False):
        return self.set_geometry((-1, -1), size, force)

    def set_geometry(self, pos, size, force = False):
        if self.get_fullscreen() and not force:
            self._fs_size_save = size
            return False

        self._window.set_geometry(pos, size)
        self._display.handle_events()
        return True

    def get_geometry(self):
        return self._window.get_geometry()

    def get_size(self):
        return self.get_geometry()[1]

    def get_pos(self):
        return self.get_geometry()[0]

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
                self.resize(self._fs_size_save, force = True)
                self._window.set_fullscreen(False)
                self._fs_size_save = None
                return True

            return False

        if self._fs_size_save:
            return False

        self._fs_size_save = self.get_size()
        display_size = self.get_display().get_size()
        self._window.set_fullscreen(True)
        self.resize(display_size, force = True)

    def get_fullscreen(self):
        return self._fs_size_save != None

    def get_id(self):
        return self._window.ptr

    def focus(self):
        return self._window.focus()


class EvasX11Window(X11Window):
    def __init__(self, gl = False, display = None, size = (640, 480),
                 title = "Evas", **kwargs):
        import kaa.evas

        if not gl:
            f = _X11.new_evas_software_x11
        else:
            f = _X11.new_evas_gl_x11

        if "parent" in kwargs:
            assert(isinstance(kwargs["parent"], X11Window))
            kwargs["parent"] = kwargs["parent"]._window

        assert(type(size) in (list, tuple))
        display = _get_display(display)
        self._evas = kaa.evas.Evas()
        window = f(self._evas._evas, display._display, size = size,
                   title = title, **kwargs)
        self._evas.output_size_set(size)
        self._evas.viewport_set((0, 0), size)

        # Ensures the display remains alive until after Evas gets deallocated
        # during garbage collection.
        self._evas._dependencies.append(display._display)
        self._evas._dependencies.append(window)
        if "parent" in kwargs:
            self._evas._dependencies.append(kwargs["parent"])
        super(EvasX11Window, self).__init__(display, window)


    def handle_events(self, events):
        needs_render = False
        for event, data in events:
            if event == X11Display.XEVENT_EXPOSE:
                self._evas.damage_rectangle_add((data["pos"], data["size"]))
                needs_render = True
            #elif event == X11Display.XEVENT_CONFIGURE_NOTIFY:
            #    if data["size"] != self._evas.output_size_get():
            #        # This doesn't act right for gl.
            #        self._evas.output_size_set(data["size"])
            #        #self._evas.viewport_set((0, 0), data["size"])
            #        needs_render = True

        super(EvasX11Window, self).handle_events(events)

        if needs_render:
            self._evas.render()
            self._display.handle_events()


    def get_evas(self):
        return self._evas
