# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# backends - Load and init the player backends
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.popcorn - Generic Player API
# Copyright (C) 2006 Jason Tackaberry, Dirk Meyer
#
# Please see the file AUTHORS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

# python imports
import os
import sys

config = []

if not __file__.startswith(sys.argv[0]):
    # import only when we are not a called child process
    from manager import *

    for backend in os.listdir(os.path.dirname(__file__)):
        dirname = os.path.join(os.path.dirname(__file__), backend)
        if os.path.isdir(dirname):
            try:
                # import the backend config
                exec('from %s.config import config as c' % backend)
                config.append((backend, c))
            except ImportError:
                continue
