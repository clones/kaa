import gst
import os

dirname = os.path.dirname(__file__)
# add our gstreamer plugins
gst.plugin_load_file(dirname + '/_gstrecord.so')

from channel import *
