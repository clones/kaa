from player import Xine
from kaa.popcorn.backends import register
from kaa.popcorn.ptypes import *

def get_capabilities():
    caps = (CAP_VIDEO, CAP_AUDIO, CAP_OSD, CAP_CANVAS, CAP_DVD, CAP_DVD_MENUS,
           CAP_DYNAMIC_FILTERS, CAP_VARIABLE_SPEED, CAP_VISUALIZATION,
           CAP_DEINTERLACE)
    schemes = [ "file", "fifo", "dvd", "vcd", "cdda", "http", "tcp", "udp",
                "rtp", "smb", "mms", "pnm", "rtsp", "pvr" ]
    exts = ["mpg", "mpeg", "iso", "avi", "mkv", "wmv", "mov", "asf"]  # FIXME: complete
    return caps, schemes, exts


register("xine", Xine, get_capabilities)
