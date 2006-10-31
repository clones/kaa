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

import os
import re

FILENAME_REGEXP = re.compile("^(.*?)_(.)(.*)$")

def fstab():
    if not os.path.isfile('/etc/fstab'):
        return []
    result = []
    regexp = re.compile('([^ \t]*)[ \t]*([^ \t]*)[ \t]*([^ \t]*)[ \t]*([^ \t]*)')
    fd = open('/etc/fstab')
    for line in fd.readlines():
        if line.find('#') >= 0:
            line = line[:line.find('#')]
        line = line.strip()
        if not line:
            continue
        if not regexp.match(line):
            continue
        device, mountpoint, type, options = regexp.match(line).groups()
        device = os.path.realpath(device)
        result.append((device, mountpoint, type, options))
    fd.close()
    return result


def get_title(name):
    """
    Convert name into a nice title
    """
    if len(name) < 2:
        return name

    if name.find('.') > 0 and not name.endswith('.'):
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
