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

def get_plugins():
    """
    Returns a dict of Plugin classes for all available plugins.
    """
    plugins = {}
    try:
        import pkg_resources
    except ImportError:
        # No setuptools.
        pass
    else:
        # Fetch a list of all entry points (defined as entry_points kwarg passed to
        # setup() for plugin modules) and load them, which returns the Plugin class
        # they were registered with.
        for entrypoint in pkg_resources.iter_entry_points('kaa.beacon.server.plugins'):
            plugins[entrypoint.name] = entrypoint.load()

    # Inspect plugins/ from kaa.beacon on-disk source tree (if there is one).
    plugindir = os.path.dirname(__file__)
    if os.path.isdir(plugindir):
        for plugin in os.listdir(plugindir):
            if not plugin.endswith('.py') or plugin == '__init__.py':
                continue
            plugin_name = plugin[:-3]
            exec('import %s as plugin' % plugin_name)
            plugins[plugin_name] = plugin.Plugin

    return plugins


def get_config():
    """
    Return the plugin config object.
    """
    config = None
    for name, plugin in get_plugins().items():
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
    for plugin in get_plugins().values():
        plugin.init(server, db)
