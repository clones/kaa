# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# config.py - kaa.base.config object for kaa.cherrypy
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.cherrypy - Web Framework for Kaa based on CherryPy
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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

__all__ = [ 'config' ]

# kaa imports
from kaa.config import Group, Var, Dict

# the config group
config = Group(desc='basic server configuration', schema=[
    Var(name='port', default=8080, desc='port to listen'),
    Var(name='debug', default=False, desc='turn on extra debug'),
    Var(name='root', default=''),
    Dict(name='static', type=str, schema=Var(type=str)) ])
