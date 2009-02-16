# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# plugin.py - Plugin loader for kaa.xmpp
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.xmpp - XMPP framework for the Kaa Media Repository
# Copyright (C) 2008 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
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

# dict of plugins
_plugins = {}

class ClientPlugin(object):
    """
    Basic plugin for Client

    @ivar client: reference to kaa.xmpp.Client object
    @ivar cache: client cache object
    """
    requires  = []

    def _extension_connect(self, client):
        """
        Connect a Client to this plugin.
        """
        self.client = client
        # bind cache object
        self.cache = client.cache
        for ext in self.requires:
            # activate extension on Client side
            client.activate_extension(ext)
        client.xmpp_connect(self)

    def _extension_activate(self):
        """
        Activate the plugin
        """
        pass

    def _extension_disconnect(self):
        self.client.xmpp_disconnect(self)
        self.client = None

    def _extension_shutdown(self):
        """
        Shutdown the plugin
        """
        pass

    def get_extension(self, name):
        """
        Get the Client extension with the given name.
        """
        return self.client.get_extension(name)

    @classmethod
    def install(cls):
        for plugin in _plugins.values():
            if plugin[1] and issubclass(cls, plugin[1]):
                plugin[1] = cls
                return
        raise AttributeError('unable to find base plugin for %s' % cls)

class RemotePlugin(object):
    """
    Basic plugin for RemoteNode

    @ivar remote: reference to kaa.xmpp.RemoteNode object
    @ivar client: reference to kaa.xmpp.Client object
    @ivar cache: RemoteNode cache object
    @cvar requires: list of extensions this extension requires
    """
    requires  = []

    def _extension_connect(self, remote):
        """
        Connect a RemoteNode to this plugin.
        """
        # bind client object
        self.client = remote.client
        self.remote = remote
        # bind cache object
        self.cache = remote.cache
        for ext in self.requires:
            remote.get_extension(ext)
        remote.xmpp_connect(self)

    def _extension_activate(self):
        """
        Activate the plugin
        """
        pass

    def _extension_disconnect(self):
        self.remote.xmpp_disconnect(self)
        self.client = None
        self.remote = None

    def _extension_shutdown(self):
        """
        Shutdown the plugin
        """
        pass

    def get_extension(self, name):
        """
        Get the RemoteNode extension with the given name.
        """
        return self.remote.get_extension(name)

    @classmethod
    def install(cls):
        for plugin in _plugins.values():
            if plugin[2] and issubclass(cls, plugin[2]):
                plugin[2] = cls
                return
        raise AttributeError('unable to find base plugin for %s' % cls)

def add_extension(name, feature, client_ext, remote_ext, auto=False):
    """
    Register a new extension
    """
    if not feature:
        feature = []
    elif not isinstance(feature, (list, tuple)):
        feature = [ feature ]
    _plugins[name] = [ feature, client_ext, remote_ext, auto ]

def enhance_client(client):
    """
    Add 'client' plugins to a Client object.
    """
    plugins = []
    for name, (disconames, client_ext, remote_ext, auto) in _plugins.items():
        if auto and client_ext:
            plugins.append(client_ext())
            # add to plugins list of shutdown
            client._plugins[name] = plugins[-1]
            setattr(client, name, plugins[-1])
            plugins[-1]._xmpp_disco = disconames
            for disconame in disconames:
                if not disconame in client.features:
                    client.features.append(disconame)
    for p in plugins:
        p._extension_connect(client)
    for p in plugins:
        p._extension_activate()

def enhance_remote_node(remote):
    """
    Add 'remote' plugins to a RemoteNode object.
    """
    plugins = []
    for name, (disconames, client_ext, remote_ext, auto) in _plugins.items():
        if auto and remote_ext:
            plugins.append(remote_ext())
            # add to plugins list of shutdown
            remote._plugins[name] = plugins[-1]
            setattr(remote, name, plugins[-1])
    for p in plugins:
        p._extension_connect(remote)
    for p in plugins:
        p._extension_activate()

def get_plugin(plugin):
    """
    Get the given plugin
    """
    if not plugin in _plugins:
        raise RuntimeError('unknown plugin %s' % plugin)
    return _plugins.get(plugin)

def get_plugin_by_namespace(ns):
    """
    Get the given plugin
    """
    for name, (disconames, client_ext, remote_ext, auto) in _plugins.items():
        if ns in disconames:
            return name
    raise RuntimeError('unknown plugin namespace %s' % ns)

def extensions(features):
    """
    List all extensions of a RemoteNode.
    """
    if features is None:
        return []
    features = features[:]
    result = []
    for name, (disconames, client_ext, remote_ext, auto) in _plugins.items():
        for disconame in disconames:
            if disconame in features:
                result.append(name)
                features.remove(disconame)
    return result
