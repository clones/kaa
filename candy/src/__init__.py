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

"""
B{kaa.candy - Third generation Canvas System using Clutter as backend}

kaa.candy is a module using clutter as canvas backend for the drawing operations.
It provides a higher level API for the basic clutter objects like Actor,
Timeline and Behaviour. The four main features are:

 1. More complex widgets. Clutter only supports basic actors Text, Texture,
    Rectangle and Group. kaa.canvas uses these primitives to create more
    powerful widgets. See the L{widgets} submodule for details.

 2. More powerful scripting language. The clutter scripting language is very
    primitive. With candyxml you can define higher level widgets and they can
    react on context changes with automatic redraws. See the L{candyxml} submodule
    for details.

 3. Better thread support. In kaa.candy two mainloops are running. The first one is
    the generic kaa mainloop and the second one is the clutter mainloop based on the
    glib mainloop. kaa.candy defines secure communication between these two mainloops.
    All widget operations should be done in the clutter thread. See the C{init},
    C{threaded} and C{Lock} in this module for details.

 4. Template engine. Instead of creating a widget it is possible to create a
    template how to create a widget. Is a a thread-safe way to create widgets by
    creating a template in the mainloop and let the clutter thread create the
    real widget based on that template. The candyxml module also uses templates
    for faster object instantiation. See L{candyxml} for details.

Because of the threading and clutter limitations you must call C{kaa.candy.init()}
in the main python file (not in an imported module) to set up kaa.candy and the
clutter thread. After that all widgets in the widgets submodule can be accessed
directly from the kaa.candy namespace.

@group Decorator: threaded
@group Submodules with classes in the kaa.candy namespace: widgets, timeline, stage
@group Submodules in the kaa.candy namespace: animation, candyxml, config
@group Additional submodules: version
"""

__all__ = [ 'threaded', 'Callback', 'Lock', 'Font', 'Color', 'Modifier', 'Properties',
            'is_template', 'init' ]

import kaa

import candyxml
import config

from core import threaded, Callback, Lock, Font, Color, Modifier, Properties, is_template

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
    Initialize kaa.candy. This sets the mainloop to the generic kaa mainloop and
    starts the glib mainloop in a thread and imports clutter and all kaa.candy
    classes depending on clutter in that thread. The function will be block until
    kaa.candy is initialized. After calling this function all widgtes and clutter
    based classes will be copied to the kaa.candy namespace.

    The function must be called from the main python file of the application because
    it imports files from a thread and python locks import statements against
    race conditions.
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
