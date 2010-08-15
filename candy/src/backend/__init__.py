# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# backend - Clutter handling and wrapper
# -----------------------------------------------------------------------------
# $Id$
#
# Access clutter functions and objects
#
# The clutter modules must be imported and used by the gobject mainloop. This
# modules wraps access to all functions, modules and other extensions of clutter
# into a single module. In the clutter mainloop you can clutter by replacing
# clutter with backend.
#
# Special clases inheriting from clutter classes will also be defined in this
# module and imported into the backend namespace when the gobject mainloop starts.
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008-2009 Dirk Meyer, Jason Tackaberry
#
# First Version: Dirk Meyer <dischi@freevo.org>
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

import sys
import logging
import kaa

log = logging.getLogger('candy')

def import_modules():
    """
    Import clutter related modules and import everything into the namespace
    of this module. This function will be called from the gobject mainloop.
    """
    import clutter
    for key in dir(clutter):
        if key[0].isalpha():
            globals()[key] = getattr(clutter, key)
    global ReflectTexture
    try:
        import libcandy
    except ImportError:
        log.exception('unable to import libcandy')
        sys.exit(0)
    ReflectTexture = libcandy.ReflectTexture

class Mainloop(object):
    """
    Clutter mainloop.
    """

    def run(self):
        # Import clutter only in the gobject thread
        # This function will be the running mainloop
        if 'clutter' in sys.modules:
            print 'kaa.candy thread failure, kaa.candy may segfault'
        try:
            import clutter
        except Exception, e:
            log.exception('unable to import clutter')
            return
        clutter.threads_init()
        import_modules()
        clutter.init()
        clutter.main()
    def quit(self):
        # Import clutter only in the gobject thread
        import clutter
        clutter.main_quit()

if 'sphinx' not in sys.modules:
    # set generic mainloop and start the clutter thread
    kaa.main.select_notifier('generic')
    kaa.gobject_set_threaded(Mainloop())
