# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__py - Interface to kaa.cherrypy
# -----------------------------------------------------------------------------
# $Id$
#
# This module define the expose decorator. The idea is copied from TurboGears.
# The expose function adds a template (Kid) and it is possible to execute the
# function from the main thread.
#
# -----------------------------------------------------------------------------
# kaa-cherrypy - Web Framework for Kaa based on CherryPy
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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

# kaa.cherrypy imports
from config import config
from server import start
from controller import expose
