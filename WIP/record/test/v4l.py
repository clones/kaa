#!/usr/bin/python

# Note for additional plugins:
# GST_PLUGIN_PATH=/usr/local/lib/gstreamer-0.10 python test/v4l.py

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
mux = gst.element_factory_make('matroskamux')
sink = gst.element_factory_make('filesink')
sink.set_property('location', 'zdf.mkv')


pipeline.add(src, video, mpeg4, mux, sink)
gst.element_link_many(src, video, mpeg4)
vpad = mux.get_compatible_pad(mpeg4.get_pad('src'))
mpeg4.get_pad('src').link(vpad)
gst.element_link_many(mux, sink)

pipeline.set_state(gst.STATE_PLAYING)
kaa.notifier.loop()
