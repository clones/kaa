#!/usr/bin/python
import pygst
pygst.require('0.10')
import gst
import sys
import time

# import kaa.notifier and set mainloop to glib
import kaa.notifier
kaa.notifier.init('gtk', x11=False)

# import kaa.record2 for the dvbtuner module
import kaa.record2

# test app logic

def bus_event(bus, message):
    t = message.type
    if t == gst.MESSAGE_EOS:
        print 'EOS'
        mainloop.quit()
    elif t == gst.MESSAGE_ERROR:
        err, debug = message.parse_error()
        print "Error: %s" % err, debug
        mainloop.quit()
    print message
    return True

if len(sys.argv) < 3:
    print 'syntax: %s <channels.conf> <channelname>' % sys.argv[0]
    sys.exit()

ccr = kaa.record2.ConfigFile( sys.argv[1] )
chan = ccr.get_channel( sys.argv[2] )
if not chan:
    print 'cannot find channel', sys.argv[2]
    sys.exit()
    
print chan.config
print 'using channel config of %s' % sys.argv[1]
print 'and searching channel %s' % sys.argv[2]

# create gstreamer pipline
pipeline = gst.Pipeline()
pipeline.get_bus().add_watch(bus_event)

# create DVBCard object and add it
dvb = kaa.record2.DVBsrc()
# FIXME: it would be nice to do
# gst.element_factory_make("dvbsrc")

dvb.set_property('adapter', 0)
dvb.set_property('channel', chan)

pipeline.add(dvb)
pipeline.set_state(gst.STATE_PLAYING)

def create_recording(filename, *pids):
    sink = gst.element_factory_make('filesink')
    sink.set_property('location', filename)
    pipeline.add(sink)
    sink.set_state(gst.STATE_PLAYING)
    dvb.get_request_pad(*pids).link(sink.get_pad('sink'))
    return sink

def stop_recording(sink):
    pad = sink.get_pad('sink')
    peer = pad.get_peer()
    peer.unlink(pad)
    dvb.remove_pad(peer)
    sink.unparent()
    sink.set_state(gst.STATE_NULL)


zdf = create_recording('zdf.ts', 545, 546)

# start 3sat in 3 seconds
kaa.notifier.OneShotTimer(create_recording, '3sat.ts', 561, 562).start(3)
# start second ZDF recording in 5 seconds
kaa.notifier.OneShotTimer(create_recording, 'zdf2.ts', 545, 546).start(5)
# stop first ZDF recording 5 seconds later
kaa.notifier.OneShotTimer(stop_recording, zdf).start(10)
kaa.notifier.loop()
