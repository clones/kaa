from player import GStreamer
from kaa.player.backends import register
from kaa.player.ptypes import *

def get_capabilities():
    caps = (CAP_VIDEO, CAP_AUDIO, CAP_OSD, CAP_CANVAS, CAP_DVD, CAP_DVD_MENUS,
           CAP_DYNAMIC_FILTERS, CAP_VARIABLE_SPEED, CAP_VISUALIZATION,
           CAP_DEINTERLACE)
    schemes = [ "file", "fifo", "dvd", "vcd", "cdda", "http", "tcp", "udp",
                "rtp", "smb", "mms", "pnm", "rtsp" ]
    exts = ["mpg", "mpeg", "iso"]  # FIXME: complete
    return caps, schemes, exts


register("gstreamer", GStreamer, get_capabilities)
