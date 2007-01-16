# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# gtkwin.py - GTK based Window classes
# -----------------------------------------------------------------------------
# $Id$
#
# FIXME: it would be much easier if we could make GTKWindow a
# X11Window and use all X11Window functions. But to do that we need to
# create a _X11.X11Window object for an already open window.
#
# -----------------------------------------------------------------------------
# kaa.display - Generic Display Module
# Copyright (C) 2007 Dirk Meyer, Jason Tackaberry
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

# kaa imports
import kaa.notifier

# kaa.display imports
from x11 import X11Display

class GTKWindow(object):
    """
    GTK based Window.
    """
    def __init__(self, window):
        self._window = window

        # FIXME: connect to GTK signals
        self.signals = kaa.notifier.Signals(
            "key_press_event", # key pressed
            "focus_in_event",  # window gets focus
            "focus_out_event", # window looses focus
            "expose_event",    # expose event
            "map_event",       # ?
            "unmap_event",     # ?
            "resize_event",    # window resized
            "configure_event") # ?

        self._display = X11Display(self._window.get_display().get_name())


    def get_size(self):
        return self._window.get_size()

    def show(self, raised = False):
        self._window.show()

    def hide(self):
        self._window.hide()

    def get_id(self):
        return self._window.xid

    def get_visible(self):
        return self._window.is_visible()

    def get_display(self):
        return self._display

    def raise_window(self):
        pass

    def lower_window(self):
        pass

    def set_visible(self, visible = True):
        if visible:
            self.show()
        else:
            self.hide()

    def handle_events(self, events):
        pass

    def move(self, pos, force = False):
        pass

    def resize(self, size, force = False):
        pass

    def set_geometry(self, pos, size, force = False):
        pass

    def get_geometry(self):
        pass

    def get_pos(self):
        pass

    def set_cursor_visible(self, visible):
        pass

    def set_cursor_hide_timeout(self, timeout):
        pass

    def set_fullscreen(self, fs = True):
        pass

    def get_fullscreen(self):
        pass

    def focus(self):
        pass



class GladeWindow(GTKWindow):
    """
    Glade based Window.
    """
    def __init__(self, gladefile, name):
        # Import glade here to avoid importing the whole gtk tree
        # when importing kaa.display.
        import gtk.glade
        self._glade = gtk.glade.XML(gladefile, name)
        GTKWindow.__init__(self, self._glade.get_widget(name).window)


    def signal_autoconnect(self, obj):
        """
        Autoconnect signals to the given object.
        """
        return self._glade.signal_autoconnect(obj)


    def get_widget(self, name):
        """
        Get widget based on name.
        """
        return self._glade.get_widget(name)
