# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# mplayer/__init__.py - mplayer backend
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.popcorn - Generic Player API
# Copyright (C) 2006 Jason Tackaberry, Dirk Meyer
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

# kaa imports
import kaa.utils

# kaa.popcorn imports
from kaa.popcorn.backends import register_backend
from kaa.popcorn.ptypes import *

# player imports
from config import config

def get_capabilities():
    """
    Return capabilities of the mplayer backend.
    """
    from player import _get_mplayer_info

    capabilities = {
        CAP_OSD : False,
        CAP_CANVAS : False,
        CAP_DYNAMIC_FILTERS : False,
        CAP_VARIABLE_SPEED : True,
        CAP_VISUALIZATION : False,

        CAP_DVD : config.capability.dvd,
        CAP_DVD_MENUS : config.capability.dvdmenu,
        CAP_DEINTERLACE : config.capability.deinterlace
    }

    mp_cmd = config.path
    if not mp_cmd:
        mp_cmd = kaa.utils.which("mplayer")
    info = _get_mplayer_info(mp_cmd)
    if not info:
        return None, None, None

    if "overlay" in info["video_filters"]:
        capabilities[CAP_OSD] = True
    if "outbuf" in info["video_filters"]:
        capabilities[CAP_CANVAS] = True

    # TODO: set CAP_VISUALIZATION if we have libvisual

    schemes = [ "file", "vcd", "cdda", "cue", "tivo", "http", "mms",
                "rtp", "rtsp", "ftp", "udp", "sdp", "dvd", "fifo" ]

    # list of extentions when to prefer this player
    exts = config.preferred.extentions.split(',')

    # list of codecs when to prefer this player
    codecs = config.preferred.codecs.split(',')

    return capabilities, schemes, exts, codecs


def register():
    from player import MPlayer
    register_backend("mplayer", MPlayer, get_capabilities)
