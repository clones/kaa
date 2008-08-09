# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# kaa.candy.widgets.py - Basic Widgets for kaa.candy
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
High level widgets for kaa.candy
"""

from ..core import Modifier
from core import Widget, Group, Texture, CairoTexture
from container import Container
from label import Label
from rectangle import Rectangle
from progressbar import Progressbar
from text import Text
from image import Image, Thumbnail
from grid import Grid, SelectionGrid
from reflection import Reflection, ReflectionModifier

__all__ = []
for key, value in globals().items():
    try:
        if issubclass(value, (Widget, Modifier)) and not value == Modifier:
            __all__.append(key)
    except TypeError:
        pass
