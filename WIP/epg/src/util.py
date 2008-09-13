# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# util.py - Small helper functions
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.epg - EPG Database
# Copyright (C) 2004,2006,2008 Jason Tackaberry, Dirk Meyer, Rob Shortt
#
# First Edition: Dirk Meyer <dischi@freevo.org>
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

class EPGError(Exception):
    pass

def cmp_channel(c1, c2):
    """
    Compare two channels for sorting.
    FIXME: a channel should have an sort number as attribute the user
    can change.
    """
    l1 = len(c1.tuner_id)
    l2 = len(c2.tuner_id)

    if l1 == 0:
        if l2 == 0:
            return 0
        else:
            return -1

    if l2 == 0:
        if l1 == 0:
            return 0
        else:
            return 1

    a = 0
    b = 0

    for t in c1.tuner_id:
        try:
            a = int(t)
            break
        except:
            if c1.tuner_id.index(t) < l1-1:
                # try next time
                continue
            else:
                break

    for t in c2.tuner_id:
        try:
            b = int(t)
            break
        except:
            if c2.tuner_id.index(t) < l2-1:
                # try next time
                continue
            else:
                break

    if a < b:
        return -1
    if a > b:
        return 1
    return 0
