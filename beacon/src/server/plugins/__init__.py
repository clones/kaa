# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# plugins - Plugin interface for Beacon
# -----------------------------------------------------------------------------
# $Id$
#
# A beacon plugin is a python file located in this plugin directory
# and needs a plugin_init function with the two paramater server and
# database. The plugin can connect to the server ipc object, register a
# callback to the parser or do something completly different. The module
# may also provide a kaa.config object that will be added to the beacon
# server config.
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006-2007 Dirk Meyer
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

import os

import kaa.config
import kaa.utils

def get_config():
    """
    Return the plugin config object.
    """
    config = None
    plugins = kaa.utils.get_plugins('kaa.beacon.server.plugins', __file__, attr='Plugin')
    for name, plugin in plugins.items():
        if hasattr(plugin, 'config'):
            if config == None:
                config = kaa.config.Group([])
            config.add_variable(name, plugin.config)
    return config


def load(server, db):
    """
    Load external plugins. Called by server on creating. The db object
    is from kaa.beacon, not kaa.db.
    """
    plugins = kaa.utils.get_plugins('kaa.beacon.server.plugins', __file__, attr='Plugin')
    for plugin in plugins.values():
        plugin.init(server, db)
