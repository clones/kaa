# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# alpha.py - Alpha functions based on clutter alpha functions
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

__all__ = [ 'alpha_inc_func', 'MAX_ALPHA' ]

import sys

MAX_ALPHA = sys.maxint

_alpha = {}

def alpha_inc_func(current_frame_num, n_frames):
    return (current_frame_num * MAX_ALPHA) / n_frames;

# register alpha functions
_alpha['inc'] = alpha_inc_func

def create(name, *args, **kwargs):
    return _alpha.get(name)

def register(name, func):
    _alpha[name] = func
