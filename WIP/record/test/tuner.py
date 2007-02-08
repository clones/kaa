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


# create gstreamer pipline

class DVBCard(gst.Pipeline):

    def __init__(self):
        gst.Pipeline.__init__(self)
        self.get_bus().add_watch(bus_event)

        self.tuner = gst.element_factory_make("dvbtuner", "tuner")

        self.tuner.set_property('debug-output', True)
        self.tuner.set_property('adapter', 0)

        frontendlist = [ "QPSK (DVB-S)", "QAM (DVB-C)", "OFDM (DVB-T)", "ATSC" ]
        frontendtype = self.tuner.get_property('frontendtype')
        print 'FRONTEND-TYPE: ', frontendlist[ frontendtype ]
        print 'FRONTEND-NAME: ', self.tuner.get_property('frontendname')
        print 'HWDECODER?   : ', self.tuner.get_property('hwdecoder')

        if frontendtype != 2:
            print 'the following code supports only DVB-T cards!'
            sys.exit()

        self.dvr = open('/dev/dvb/adapter0/dvr0')
        self.src = gst.element_factory_make("fdsrc")
        self.src.set_property('fd', self.dvr.fileno())
        self.queue = gst.element_factory_make("queue")
        self.splitter = gst.element_factory_make("tssplitter")
        self.splitter.connect("pad-added", self._on_new_pad)
        self.add(self.src, self.queue, self.splitter)
        self.src.link(self.queue)
        self.queue.link(self.splitter)
        self.set_state(gst.STATE_PLAYING)
        print 'go'
        self.mapping = {}
        self.pids = []
        kaa.notifier.Timer(self._debug).start(1)


    def _debug(self):
        print self.tuner.get_property('status')

    def tune(self, channel):
        # tuning to ZDF (hardcoded values! change them!)
        self.tuner.set_property("frequency", 562000000)
        self.tuner.set_property("inversion", 2)
        self.tuner.set_property("bandwidth", 0)
        self.tuner.set_property("code-rate-high-prio", 2)
        self.tuner.set_property("code-rate-low-prio", 0)
        self.tuner.set_property("constellation", 1)
        self.tuner.set_property("transmission-mode", 1)
        self.tuner.set_property("guard-interval", 2)
        self.tuner.set_property("hierarchy", 0)

        # tune to channel
        self.tuner.emit("tune")
        
    def _on_new_pad(self, splitter, pad):
        print "pad added!"
        print 'PAD:',pad
        print 'PADNAME:',pad.get_name()
        print 'PADCAPS:',pad.get_caps()
        sink = self.mapping[pad.get_name()]
        pad.link(sink.get_pad('sink'))


    def add_filter(self, sink, *pids):
        for pid in pids:
            if not pid in self.pids:
                self.tuner.emit("add-pid", pid)
                self.pids.append(pid)
        self.add(sink)
        self.mapping[sink.get_name()] = sink
        pidstr = ','.join([str(p) for p in pids])
        self.splitter.emit("set-filter", sink.get_name(), pidstr)

c = DVBCard()
c.tune(None)

# record ZDF
sink = gst.element_factory_make('filesink')
sink.set_property('location', 'zdf.ts')
c.add_filter(sink, 545, 546)
sink.set_state(gst.STATE_PLAYING)

def recording2():
    # record 3sat
    sink = gst.element_factory_make('filesink')
    sink.set_property('location', '3sat.ts')
    c.add_filter(sink, 561, 562)
    sink.set_state(gst.STATE_PLAYING)

def recording3():
    # record ZDF again
    sink = gst.element_factory_make('filesink')
    sink.set_property('location', 'zdf2.ts')
    c.add_filter(sink, 545, 546)
    sink.set_state(gst.STATE_PLAYING)

# start 3sat in 3 seconds
kaa.notifier.OneShotTimer(recording2).start(3)
# start second ZDF recording in 5 seconds
kaa.notifier.OneShotTimer(recording3).start(5)
kaa.notifier.loop()
