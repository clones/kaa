from player import Xine
from kaa.popcorn.backends import register
from kaa.popcorn.ptypes import *

def get_capabilities():
    capabilities = {
        CAP_CANVAS : True,
        CAP_CANVAS : True,
        CAP_DYNAMIC_FILTERS : False,
        CAP_VARIABLE_SPEED : True,
        CAP_VISUALIZATION : True,

        CAP_DVD : 8,
        CAP_DVD_MENUS : 8,
        CAP_DEINTERLACE : 8
    }
    schemes = [ "file", "fifo", "dvd", "vcd", "cdda", "http", "tcp", "udp",
                "rtp", "smb", "mms", "pnm", "rtsp", "pvr" ]

    # list of extentions when to prefer this player
    exts = ["mpg", "mpeg", "iso"]

    # list of codecs when to prefer this player
    codecs = []

    return capabilities, schemes, exts, codecs


register("xine", Xine, get_capabilities)
