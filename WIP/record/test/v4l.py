#!/usr/bin/python

# Note for additional plugins:
# GST_PLUGIN_PATH=/usr/local/lib/gstreamer-0.10 python test/v4l.py
# mplayer tv:// -tv driver=v4l:width=640:height=480

import os
os.environ['GST_PLUGIN_PATH'] = '/usr/local/lib/gstreamer-0.10'

import pygst
pygst.require('0.10')
import gst
import sys
import time

# import kaa.notifier and set mainloop to glib
import kaa.notifier
kaa.notifier.init('gtk', x11=False)

def bus_event(bus, message):
    t = message.type
    if t == gst.MESSAGE_EOS:
        print 'EOS'
        sys.exit(0)
    elif t == gst.MESSAGE_ERROR:
        err, debug = message.parse_error()
        print "Error: %s" % err, debug
        sys.exit(0)
    print message
    return True

pipeline = gst.Pipeline()
pipeline.get_bus().add_watch(bus_event)

src = gst.element_factory_make('v4lsrc')
video = gst.element_factory_make('queue')
mpeg4 = gst.element_factory_make('ffenc_mpeg4')
mpeg4.set_property('bitrate', 800)
mpeg4.set_property('pass', 'quant')
mpeg4.set_property('quantizer', 10)
mpeg4.set_property('flags', 0x00000004 | 0x00000040 | 0x00200000)

mux = gst.element_factory_make('matroskamux')
sink = gst.element_factory_make('filesink')
sink.set_property('location', '/local/testvideo.mkv')


pipeline.add(src, video, mpeg4, mux, sink)
gst.element_link_many(src, video, mpeg4)
vpad = mux.get_compatible_pad(mpeg4.get_pad('src'))
mpeg4.get_pad('src').link(vpad)
gst.element_link_many(mux, sink)

pipeline.set_state(gst.STATE_PLAYING)
kaa.notifier.loop()
