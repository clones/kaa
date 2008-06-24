# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# kaa.candy - Third generation Canvas System using Clutter as backend
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

import kaa

from decorator import gui_execution

class Mainloop(object):
    """
    Clutter mainloop.
    """

    def run(self):
        # Import clutter only in the gobject thread
        # This function will be the running mainloop
        import clutter
        clutter.threads_init()
        clutter.init()
        clutter.main()
    def quit(self):
        # Import clutter only in the gobject thread
        import clutter
        clutter.main_quit()

def init():
    """
    Set the mainloop and load the widgets into our namespace
    """
    @gui_execution()
    def load_modules():
        import xmlparser as _xmlparser
        global xmlparser
        xmlparser = _xmlparser
        global Properties
        from properties import Properties
        global Timeline, MasterTimeline
        from timeline import Timeline, MasterTimeline
        global Color, Font
        from core import Color, Font
        global Widget, Group, Text, Texture, Imlib2Texture, CairoTexture, Container, Label, Rectangle, Progressbar
        from widgets import Widget, Group, Text, Texture, Imlib2Texture, CairoTexture, Container, Label, Rectangle, Progressbar
        global Stage
        from stage import Stage
        import animation as _animation
        global animation
        animation = _animation
        
    # set generic notifier and start the clutter thread
    kaa.main.select_notifier('generic')
    kaa.gobject_set_threaded(Mainloop())
    load_modules()

# we need an extra init function and that function _must_ be
# called directly when the application starts. It is not possible
# to import clutter in a thread while we are in an import ourself
#
# The following code is a hack around this problem:
#
# import imp
# # release the lock of this import (ouch!)
# imp.release_lock()
# try:
#     init()
# finally:
#     # set the lock back so nobody will notice what we have done
#     imp.acquire_lock()
