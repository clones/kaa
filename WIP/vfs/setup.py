# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# setup.py - Setup script for kaa.vfs
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-vfs - Media VFS
# Copyright (C) 2005 Jason Tackaberry, Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
#                Jason Tackaberry <tack@sault.org>
# Maintainer:    The Kaa team
#
# Please see the file doc/CREDITS for a complete list of authors.
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
import sys

try:
    # kaa base imports
    from kaa.base.distribution import Extension, setup
except ImportError:
    print 'kaa.base not installed'
    sys.exit(1)

# check for libdvdread
ifoparser = Extension('kaa/metadata/disc/ifoparser', ['src/disc/ifomodule.c'],
                      libraries=[ 'dvdread' ])

setup (module      = 'vfs',
       version     = '0.1',
       description = "Media-oriented VFS"
      )
