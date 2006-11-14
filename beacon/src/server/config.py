# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# config.py - Beacon Server Config
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
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

__all__ = [ 'config' ]

# kaa imports
from kaa.config import Config, Group, Var, List, Dict

config = Config(desc='Beacon configuration', schema = [

    List(name = 'monitors',
         schema = Var(type = str, desc='Path of directory', default = ''),
         desc = '''
         List of directories to monitor, e.g.

         monitors[0] = /media/mp3
         monitors[1] = $(HOME)/mp3
         '''),

    # crawler settings
    Group(name = 'crawler',
          desc = 'Settings for filesystem crawler',
          schema= [

    Var(name = 'scantime',
        default = 0.04,
        desc = """
        Internal timer for scanning. Decreasing it will speed up the scanner
        but slow down the system. Increasing it will save CPU time and slow
        machines.
        """),

    Var(name = 'rescan_growing',
        default = 10,
        desc = """
        Internal in seconds how often still growing files should be checked
        """)
    ]),

    # plugins
    Dict(name = 'plugins',
         schema = Var(type = bool, desc = 'Enable plugin', default = False),
         desc = 'Dict of plugins to enable (True/False)')
])
