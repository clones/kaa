# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# db.py - Database to store client cache
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

__all__ = [ 'Database' ]

# python imports
import os
import cPickle as pickle

# kaa imports
import kaa
import kaa.net.tls

import config

class Entity(object):
    """
    Config for one entity (Client or RemoteNode)
    """
    def __init__(self, db, change_callback):
        self._dict = db
        self._changed = change_callback

    def __getattr__(self, attr):
        """
        Get attribute value or None if it does not exist.
        """
        if attr.startswith('_'):
            return super(Entity, self).__getattr__(attr)
        return self._dict.get(attr)

    def __setattr__(self, attr, value):
        """
        Set attribute to a new value and schedule database save
        """
        if attr.startswith('_'):
            return super(Entity, self).__setattr__(attr, value)
        if self._dict.get(attr) == value:
            return
        if value is None:
            del self._dict[attr]
        else:
            self._dict[attr] = value
        self._changed()


class Database(Entity):
    """
    Config for a client
    """
    def __init__(self, appname):
        super(Database, self).__init__({}, self._changed)
        self._filename = os.path.join(config.cachedir, appname + '.db')
        if not os.path.isdir(config.cachedir):
            os.mkdir(config.cachedir, 0700)
        if os.path.isfile(self._filename):
            f = open(self._filename, 'rb')
            self._dict = pickle.load(f)
            f.close()
        self._nodes = {}

    @kaa.timed(0, kaa.OneShotTimer, kaa.POLICY_ONCE)
    def _changed(self):
        """
        Save Database.
        """
        f = open(self._filename, 'wb')
        pickle.dump(self._dict, f, -1)
        f.close()

    def get_node(self, jid):
        """
        Get RemoteNode info.
        """
        key = '_xmpp_%s' % jid
        if key in self._nodes:
            return self._nodes[key]
        if not key in self._dict:
            self._dict[key] = dict(jid=jid)
        return Entity(self._dict[key], self._changed)

    def __getattr__(self, attr):
        """
        Get attribute value or None if it does not exist.
        """
        return super(Database, self).__getattr__(attr)

    def __setattr__(self, attr, value):
        """
        Set attribute to a new value and schedule database save
        """
        return super(Database, self).__setattr__(attr, value)
