# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.mevas
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-mevas - MeBox Canvas System
# Copyright (C) 2004-2005 Jason Tackaberry <tack@sault.org>
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
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

import os
import distutils.core

# create fake kaa.__init__.py
open('__init__.py', 'w').close()

# call setup
distutils.core.setup(
    name        = 'kaa-mevas',
    version     = '0.1',
    package_dir = {'kaa': ".", 'kaa.mevas': 'src',
                   'kaa.mevas.imagelib': "src/imagelib",
                   'kaa.mevas.displays': 'src/displays' },
    packages    = ['kaa', 'kaa.mevas', 'kaa.mevas.imagelib',
                   'kaa.mevas.displays'],
    )

# delete fake kaa.__init__.py
os.unlink('__init__.py')
