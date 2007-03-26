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

from kaa.record2.v4l import V4Lsrc

def bus_event(bus, message):
    t = message.type
    if t == gst.MESSAGE_EOS:
        print 'EOS'
        sys.exit(0)
    elif t == gst.MESSAGE_ERROR:
        err, debug = message.parse_error()
        print "Error: %s" % err, debug
        sys.exit(0)
    elif t == gst.MESSAGE_STATE_CHANGED:
        if message.src == src and message.parse_state_changed()[1] == gst.STATE_PLAYING:
            print 'go'

    print message
    return True

pipeline = gst.Pipeline()
pipeline.get_bus().add_watch(bus_event)

src = V4Lsrc()
# src.set_property('frequency', 196250)
src.set_property('norm', 'pal')
src.set_property('chanlist', 'europe-west')
src.set_property('channel', 'E8')

deinterlace = gst.element_factory_make('deinterlace')

mpeg4 = gst.element_factory_make('ffenc_mpeg4')
mpeg4.set_property('bitrate', 5000)
mpeg4.set_property('pass', 'quant')
mpeg4.set_property('quantizer', 10)
mpeg4.set_property('flags', 0x00000004 | 0x00000040 | 0x00200000)

mux = gst.element_factory_make('matroskamux')
sink = gst.element_factory_make('filesink')
sink.set_property('location', 'testvideo.mkv')

pipeline.add(src, deinterlace, mpeg4, mux, sink)
gst.element_link_many(src, deinterlace, mpeg4)

vpad = mux.get_compatible_pad(mpeg4.get_pad('src'))
mpeg4.get_pad('src').link(vpad)
gst.element_link_many(mux, sink)

# audio = gst.element_factory_make('alsasrc')
# audio.set_property('device', '/dev/sound/dsp')
# pipeline.add(audio)
# apad = mux.get_compatible_pad(audio.get_pad('src'))
# audio.get_pad('src').link(apad)

pipeline.set_state(gst.STATE_PLAYING)

kaa.notifier.loop()
