import kaa.utils

from player import MPlayer, _get_mplayer_info
from kaa.popcorn.backends import register
from kaa.popcorn.ptypes import *
from config import config

def get_capabilities():

    capabilities = {
        CAP_CANVAS : False,
        CAP_CANVAS : False,
        CAP_DYNAMIC_FILTERS : False,
        CAP_VARIABLE_SPEED : True,
        CAP_VISUALIZATION : True,

        CAP_DVD : 8,
        CAP_DVD_MENUS : 1,
        CAP_DEINTERLACE : 8
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

    schemes = ["file", "vcd", "cdda", "cue", "tivo", "http", "mms", "rtp",
                "rtsp", "ftp", "udp", "sdp", "dvd", "fifo"]

    # list of extentions when to prefer this player
    exts = ["mpg", "mpeg", "mov"]

    # list of codecs when to prefer this player
    codecs = []

    return capabilities, schemes, exts, codecs

register("mplayer", MPlayer, get_capabilities)
