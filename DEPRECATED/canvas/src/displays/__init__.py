# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.canvas - Canvas library based on kaa.evas
# Copyright (C) 2005, 2006 Jason Tackaberry
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

from buffer import *

try:
    from x11 import *
except ImportError:
    pass

try:
    from fb import *
except ImportError:
    pass

try:
    from dfb import *
except ImportError:
    pass
