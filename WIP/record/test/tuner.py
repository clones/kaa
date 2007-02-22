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

class DVBCard(gst.Bin):

    def __init__(self, *args):
        gst.Bin.__init__(self, *args)
        self._tuner = gst.element_factory_make("dvbtuner", "tuner")

        self._tuner.set_property('debug-output', True)
        self._tuner.set_property('adapter', 0)

        frontendlist = [ "QPSK (DVB-S)", "QAM (DVB-C)", "OFDM (DVB-T)", "ATSC" ]
        frontendtype = self._tuner.get_property('frontendtype')
        print 'FRONTEND-TYPE: ', frontendlist[ frontendtype ]
        print 'FRONTEND-NAME: ', self._tuner.get_property('frontendname')
        print 'HWDECODER?   : ', self._tuner.get_property('hwdecoder')

        if frontendtype != 2:
            print 'the following code supports only DVB-T cards!'
            sys.exit()

        self._dvr = open('/dev/dvb/adapter0/dvr0')
        self._src = gst.element_factory_make("fdsrc")
        self._src.set_property('fd', self._dvr.fileno())
        self._queue = gst.element_factory_make("queue")
        self._splitter = gst.element_factory_make("tssplitter")
        self._splitter.connect("pad-added", self._on_new_pad)
        self.add(self._src, self._queue, self._splitter)
        self._src.link(self._queue)
        self._queue.link(self._splitter)
        self._pids = []
        kaa.notifier.Timer(self._debug).start(1)


    def _debug(self):
        print self._tuner.get_property('status')


    def tune(self, channel):
        if not channel:
            print 'no channel given - FIXME'
            sys.exit()
        
        frontendtype = self._tuner.get_property('frontendtype')
        if frontendtype == 0:
            # TODO FIXME broken --> fixme
            DVBS
        elif frontendtype == 1:
            # TODO FIXME broken --> fixme
            DVBC
        elif frontendtype == 2:
            # TODO FIXME I have to fix parser and tuner! - they should use the same keywords
            channel.config['constellation'] = channel.config['modulation']
            
            for cfgitem in [ 'frequency', 'inversion', 'bandwidth', 'code-rate-high-prio', 'code-rate-low-prio', 'constellation', 'transmission-mode', 'guard-interval', 'hierarchy' ]:
                print '%s ==> %s' % (cfgitem, channel.config[ cfgitem ])
                self._tuner.set_property( cfgitem, channel.config[ cfgitem ] )
                      
        elif frontendtype == 3:
            # TODO FIXME broken --> fixme
            ATSC
        else:
            print 'OH NO! Please fix this code!'
            

        # tune to channel
        self._tuner.emit("tune")

    def _on_new_pad(self, splitter, pad):
        self.add_pad(gst.GhostPad(pad.get_name(), pad))

    def add_filter(self, name, *pids):
        for pid in pids:
            if not pid in self._pids:
                self._tuner.emit("add-pid", pid)
                self._pids.append(pid)
        pidstr = ','.join([str(p) for p in pids])
        self._splitter.emit("set-filter", name, pidstr)


    def remove_filter(self, name):
        # TODO FIXME remove pids from tuner
        self._splitter.emit("remove-filter", name)



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


mapping = {}

def on_new_pad(dvb, pad):
    sink = mapping[pad.get_name()]
    pad.link(sink.get_pad('sink'))

if len(sys.argv) < 3:
    print 'syntax: %s <channels.conf> <channelname>' % sys.argv[0]
    sys.exit()

ccr = kaa.record2.ConfigFile( sys.argv[1] )
chan = ccr.get_channel( sys.argv[2] )
if not chan:
    print 'cannot find channel', sys.argv[2]
    sys.exit()
    
print chan.config

# create gstreamer pipline
pipeline = gst.Pipeline()
pipeline.get_bus().add_watch(bus_event)

# create DVBCard object and add it
c = DVBCard()
c.connect("pad-added", on_new_pad)

pipeline.add(c)
pipeline.set_state(gst.STATE_PLAYING)

print 'using channel config of %s' % sys.argv[1]
print 'and searching channel %s' % sys.argv[2]



# now the testing starts by tuning
c.tune(chan)


def create_recording(filename, *pids):
    sink = gst.element_factory_make('filesink')
    sink.set_property('location', filename)
    pipeline.add(sink)
    sink.set_state(gst.STATE_PLAYING)
    mapping[filename] = sink
    c.add_filter(filename, *pids)


def stop_recording(filename):
    c.remove_filter(filename)


create_recording('zdf.ts', 545, 546)

# start 3sat in 3 seconds
kaa.notifier.OneShotTimer(create_recording, '3sat.ts', 561, 562).start(3)
# start second ZDF recording in 5 seconds
kaa.notifier.OneShotTimer(create_recording, 'zdf2.ts', 545, 546).start(5)
# stop second ZDF recording 5 seconds later
kaa.notifier.OneShotTimer(stop_recording, 'zdf2.ts').start(10)
kaa.notifier.loop()
