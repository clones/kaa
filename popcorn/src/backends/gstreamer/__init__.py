from player import GStreamer
from kaa.popcorn.backends import register
from kaa.popcorn.ptypes import *

def get_capabilities():
    capabilities = {
        CAP_CANVAS : False,
        CAP_CANVAS : False,
        CAP_DYNAMIC_FILTERS : False,
        CAP_VARIABLE_SPEED : False,
        CAP_VISUALIZATION : True,

        CAP_DVD : 0,
        CAP_DVD_MENUS : 0,
        CAP_DEINTERLACE : 8
    }
    schemes = [ "file", "fifo", "dvd", "vcd", "cdda", "http", "tcp", "udp",
                "rtp", "smb", "mms", "pnm", "rtsp" ]

    # list of extentions when to prefer this player
    exts = ["mpg", "mpeg", "iso"]

    # list of codecs when to prefer this player
    codecs = []

    return capabilities, schemes, exts, codecs


register("gstreamer", GStreamer, get_capabilities)
