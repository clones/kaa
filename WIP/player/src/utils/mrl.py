# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# __init__.py - Generic Player Interface
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-player - Generic Player API
# Copyright (C) 2006 Jason Tackaberry, Dirk Meyer
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
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
import stat
import re

def parse_mrl(mrl):
    """
    Parses a mrl, returning a 2-tuple (scheme, path) where scheme is the mrl
    scheme such as file, dvd, fifo, udp, etc., and path is the whatever
    follows the mrl scheme.  If no mrl scheme is specified in 'mrl', it
    attempts to make an intelligent choice.
    """
    scheme, path = re.search("^(\w{,4}:)?(.*)", mrl).groups()
    if not scheme:
        scheme = "file"
        try:
            stat_info = os.stat(path)
        except OSError:
            return scheme, path

        if stat_info[stat.ST_MODE] & stat.S_IFIFO:
            scheme = "fifo"
        else:
            try:
                f = open(path)
            except (OSError, IOError):
                return scheme, path
            f.seek(32768, 0)
            b = f.read(60000)
            if b.find("UDF") != -1:
                b = f.read(550000)
                if b.find('OSTA UDF Compliant') != -1 or b.find("VIDEO_TS") != -1:
                    scheme = "dvd"
    else:
        scheme = scheme[:-1]
    return scheme, path
