import kaa.utils

from player import MPlayer, _get_mplayer_info
from kaa.popcorn.backends import register
from kaa.popcorn.ptypes import *

def get_capabilities():
    capabilities = [CAP_VIDEO, CAP_AUDIO, CAP_DVD, CAP_VARIABLE_SPEED]
    mp_cmd = kaa.utils.which("mplayer")
    info = _get_mplayer_info(mp_cmd)
    if not info:
        return None, None, None

    if "overlay" in info["video_filters"]:
        capabilities.append(CAP_OSD)
    if "outbuf" in info["video_filters"]:
        capabilities.append(CAP_CANVAS)

    schemes = ["file", "vcd", "cdda", "cue", "tivo", "http", "mms", "rtp",
                "rtsp", "ftp", "udp", "sdp", "dvd", "fifo"]

    exts = ["avi", "wmv", "mkv", "asf", "mov"]  # FIXME: complete.
    return capabilities, schemes, exts

register("mplayer", MPlayer, get_capabilities)
