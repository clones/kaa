#!/usr/bin/python
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

def new_pad(demux, pad):
    print '--->', pad.get_name()
    if pad.get_name().startswith('video'):
        pad.link(video.get_pad('sink'))
    else:
        pad.link(audio.get_pad('sink'))

# create gstreamer pipline

pipeline = gst.Pipeline()
pipeline.get_bus().add_watch(bus_event)

src = gst.element_factory_make('filesrc')
src.set_property('location', 'zdf.ts')

demux = gst.element_factory_make('ffdemux_mpegts')
demux.connect("pad-added", new_pad)

pipeline.add(src, demux)
src.link(demux)


# audio code

audio = gst.element_factory_make('queue')
mp2a = gst.element_factory_make('ffdec_mp3')
aac = gst.element_factory_make('faac')

pipeline.add(audio, mp2a, aac)
gst.element_link_many(audio, mp2a, aac)

# video code

video = gst.element_factory_make('queue')
mp2v = gst.element_factory_make('mpeg2dec')
mpeg4 = gst.element_factory_make('ffenc_mpeg4')

pipeline.add(video, mp2v, mpeg4)
gst.element_link_many(video, mp2v, mpeg4)


# muxer

mux = gst.element_factory_make('matroskamux')
# mux = gst.element_factory_make('ffmux_mov')
sink = gst.element_factory_make('filesink')
sink.set_property('location', 'zdf.mkv')

pipeline.add(mux, sink)
mux.link(sink)

# normal link does not work!!!!!
vpad = mux.get_compatible_pad(mpeg4.get_pad('src'))
mpeg4.get_pad('src').link(vpad)

apad = mux.get_compatible_pad(aac.get_pad('src'))
aac.get_pad('src').link(apad)

pipeline.set_state(gst.STATE_PLAYING)
kaa.notifier.loop()
