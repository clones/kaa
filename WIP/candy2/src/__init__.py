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

import candyxml
import config

from core import threaded, Lock, Font, Color, Properties, is_template

class _Mainloop(object):
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
    @threaded()
    def load_modules():
        """
        Load submodules in the clutter thread and add some classes
        to globals()
        """
        import animation
        import widgets
        # copy all widgets in the kaa.candy namespace
        for key in widgets.__all__:
            globals()[key] = getattr(widgets, key)
        # copy some extra classes into the kaa.candy namespace
        global Timeline, MasterTimeline, Stage
        from timeline import Timeline, MasterTimeline
        from stage import Stage

    # set generic notifier and start the clutter thread
    kaa.main.select_notifier('generic')
    kaa.gobject_set_threaded(_Mainloop())
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
