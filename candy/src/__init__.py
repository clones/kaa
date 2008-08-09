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
    All widget operations starting with _candy must be called in the clutter thread.

 4. Template engine. Instead of creating a widget it is possible to create a
    template how to create a widget. The candyxml module uses templates for faster
    object instantiation. See L{candyxml} for details.


Each widget has a clutter actor and functions starting with C{_candy_} to
create and modify the clutter actors. These functions will always be
executed in the clutter mainloop. Do not access the internal object from
any other function.

For basic functions read the Widget class documentation and the clutter
U{Actor API <http://www.clutter-project.org/docs/clutter/0.6/ClutterActor.html>}.
"""

__all__ = [ 'Font', 'Color', 'Modifier', 'Properties', 'Stage', 'is_template',
            'Animation', 'thread_enter', 'thread_leave' ]

import sys
import candyxml
import config

from core import Font, Color, Modifier, Properties, is_template
from animation import Animation, thread_enter, thread_leave
from widgets import *
from stage import Stage

import widgets

for key in widgets.__all__:
    __all__.append(key)

if 'epydoc' in sys.modules:
    # epydoc magic, update our docstring
    _w = [ w for w in widgets.__all__ if issubclass(getattr(widgets, w), Widget) ]
    __doc__ += '@group Widgets: ' + ', '.join(_w) + '\n'
    _m = []
    for key, value in globals().items():
        try:
            if issubclass(value, Modifier):
                _m.append(key)
        except TypeError:
            pass
    __doc__ += '@group Modifier: ' + ', '.join(_m) + '\n'
