# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# utils.py - small helper functions
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
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

# python imports
import re
import os
import socket
import ctypes, ctypes.util


FILENAME_REGEXP = re.compile("^(.*?)_(.)(.*)$")

def get_title(name, strip=True):
    """
    Convert name into a nice title
    """
    if len(name) < 2:
        return name

    if strip and name.find('.') > 0 and not name.endswith('.'):
        name = name[:name.rfind('.')]

    # TODO: take more hints
    if name.upper() == name:
        name = name.lower()
    name = name[0].upper() + name[1:]
    while True:
        m = FILENAME_REGEXP.match(name)
        if not m:
            break
        name = m.group(1) + ' ' + m.group(2).upper() + m.group(3)
    if name.endswith('_'):
        name = name[:-1]
    return name


def get_machine_uuid():
    """
    Returns a unique (and hopefully persistent) identifier for the current
    machine.

    This function will return the D-Bus UUID if it exists (which should be
    available on modern Linuxes), otherwise it will return the machine's
    hostname.
    """
    # First try libdbus.
    try:
        lib = ctypes.CDLL(ctypes.util.find_library('dbus-1'))
        ptr = lib.dbus_get_local_machine_id()
        uuid = ctypes.c_char_p(ptr).value
        lib.dbus_free(ptr)
        return uuid
    except AttributeError:
        pass

    # Next try to read from filesystem at well known locations.
    for dir in '/var/lib/dbus', '/etc/dbus-1':
        try:
            return file(os.path.join(dir, 'machine-id')).readline().strip()
        except IOError:
            pass

    # No dbus, fallback to hostname.
    return socket.getfqdn()
