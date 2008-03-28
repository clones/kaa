# Note: this requires kaa.base from
# svn://svn.freevo.org/kaa/trunk/base to be installed
#
# Thread information:
#
# There are two threads running here. One is the kaa mainloop (default) and
# the other one is the gobject mainloop. Functions decorated with the threaded
# decorator force execution of the function in the mainthread or the gobject
# thread.

import kaa

kaa.main.select_notifier('generic')
kaa.gobject_set_threaded()

import gst

class DVB(object):

    def __init__(self, adapter, frontend):
        """
        Thread Information: created by the main thread
        """
        self.signals = kaa.Signals('state-change', 'lock')
        self.adapter = adapter
        self.frontend = frontend
        self.type = None
        self.streams = {}
        self.pipeline =  gst.parse_launch(
            "dvbbasebin name=dvbsrc adapter=%d frontend=%d " \
            "stats-reporting-interval=0 ! queue ! " \
            "fakesink silent=true" % (self.adapter, self.frontend))
        self.state = None
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_watch_func)
        dvbsrc = self.pipeline.get_by_name("dvbsrc")
        dvbsrc.connect("pad-added", self._pad_added)
        dvbsrc.connect("pad-removed", self._pad_removed)

    @kaa.threaded(kaa.MAINTHREAD)
    def bus_watch_func(self, bus, message):
        """
        Thread Information: called by gobject but forced into main thread
        This code is not needed right now
        """
        # needed for scanning
        # print message
        # return
        if message.type == gst.MESSAGE_STATE_CHANGED:
            # print message
            return
        if message.type == gst.MESSAGE_ELEMENT:
            if message.structure.get_name() == 'dvb-adapter':
                self.type = message.structure['type']
                return
            if message.structure.get_name() == 'dvb-frontend-stats':
                if message.structure["lock"]:
                    self.signals['lock'].emit()
                return
            if message.structure.get_name() == 'nit':
                print 'nit'
                s = message.structure
                name = s['network-id']
                actual = s['actual-network']
                if s.has_key('network-name'):
                    name = s['network-name']
                transports = s['transports']
                for transport in transports:
                    tsid = transport['transport-stream-id']
                    print transport.keys()
                    if transport.has_key('delivery'):
                        delivery = transport['delivery']
                        # delivery['frequency']
                return
            if message.structure.get_name() == 'pat':
                # print message.structure.keys()
                programs = message.structure['programs']
                for p in programs:
                    # print p.keys()
                    sid = p['program-number']
                    pmt = p['pid']
                    # e.g. sid 160 (Das Erste) on pmt 260
                    # print 'found program %s on pid %s' % (sid, pmt)
                    dvbsrc = self.pipeline.get_by_name("dvbsrc")
                return
            if message.structure.get_name() == 'sdt':
                s = message.structure
                if s["actual-transport-stream"]:
                    for service in s["services"]:
                        name = service.get_name()
                        sid = int(name[8:])
                        if service.has_key("name"):
                            name = service["name"]
                        # e.g. Das Erste with sid=160 # tsid=3329
                        print name, sid #, s["transport-stream-id"]
                return
            if message.structure.get_name() == 'pmt':
                s = message.structure
                # e.g. 160 (ARD)
                # print 'pmt for', s['program-number']
                # for stream in s['streams']:
                #     print '', stream.keys()
                #     print stream['pid'], stream['stream-type'], stream['descriptors']
                return
            if message.structure.get_name() == 'eit':
                # print message.structure.keys()
                return
            print 'Bus watch function for message %r' % message

    def _pad_added(self, element, pad):
        """
        Thread Information: called by gobject thread
        """
        print 'START', pad
        sid = pad.get_name()[8:]
        if sid == '0':
            return
        pad.link(self.streams[sid].get_pad())

    def _pad_removed(self, bin, pad):
        """
        Thread Information: called by gobject thread
        """
        print 'STOP', pad

    @kaa.threaded(kaa.GOBJECT)
    def tune(self, tuning_data):
        """
        Thread Information: called by main but forced into gobject thread
        """
        dvbsrc = self.pipeline.get_by_name("dvbsrc")
        print 'BEGIN TUNE', kaa.is_mainthread()
        print 'set ready'
        element = self.pipeline
        if dvbsrc.get_state()[1] == gst.STATE_PLAYING:
            element = dvbsrc
        # XXX This sometimes blocks on re-tuning. Sometimes it is non blocking,
        # XXX sometimes it blocks for 10 or 20 seconds and sometimes it does not
        # XXX return after over a minute when I killed the app.
        element.set_state(gst.STATE_READY)
        print dvbsrc.get_state()
        print 'tune'
        for key, value in tuning_data.items():
            dvbsrc.set_property(key, value)
        element.set_state(gst.STATE_PLAYING)
        print dvbsrc.get_state()
        print 'END TUNE'


    def get_stream(self, sid):
        """
        Thread Information: called by main thread
        """
        if not str(sid) in self.streams:
            self.streams[str(sid)] = Stream(self, sid=str(sid))
        return self.streams[str(sid)]


    def _stream_activate(self, stream):
        """
        Thread Information: called by gobject thread
        """
        dvbsrc = self.pipeline.get_by_name("dvbsrc")
        programs = dvbsrc.get_property("program-numbers").split(':')
        if not stream.sid in programs:
            programs.append(stream.sid)
        dvbsrc.set_property("program-numbers", ':'.join(programs))


    def _stream_deactivate(self, stream):
        """
        Thread Information: called by gobject thread
        """
        dvbsrc = self.pipeline.get_by_name("dvbsrc")
        programs = dvbsrc.get_property("program-numbers").split(':')
        if stream.sid in programs:
            programs.remove(stream.sid)
        programs = ':'.join(programs)
        if not programs:
            programs = ':'
        dvbsrc.set_property("program-numbers", programs)


class Stream(object):
    """
    'queue ! tee' bin for recordings
    """
    def __init__(self, device, **kwargs):
        """
        Thread Information: created by the main thread
        """
        self.device = device
        self.bin = None
        self.sinks = 0
        for key, value in kwargs.items():
            setattr(self, key, value)

    @kaa.threaded(kaa.GOBJECT)
    def append(self, sink):
        """
        Thread Information: called by main but forced into gobject thread
        """
        if self.bin == None:
            print 'create stream'
            self.bin = gst.parse_bin_from_description('queue ! tee name=tee', True)
            self.device.pipeline.add(self.bin)
            self.device._stream_activate(self)
            self.bin.set_state(gst.STATE_PLAYING)
        print 'start', sink
        self.bin.add(sink)
        pad = self.bin.get_by_name("tee").get_request_pad('src%d')
        pad.link(sink.get_pad('sink'))
        sink.set_state(gst.STATE_PLAYING)
        self.sinks += 1

    @kaa.threaded(kaa.GOBJECT)
    def remove(self, sink):
        """
        Thread Information: called by main but forced into gobject thread
        """
        print 'BEGIN remove', sink
        self.sinks -= 1
        self.bin.get_by_name("tee").unlink(sink)
        sink.set_state(gst.STATE_NULL)
        sink.get_state()
        self.bin.remove(sink)
        if self.sinks:
            print 'END remove', sink
            return
        print 'remove stream'
        self.device._stream_deactivate(self)
        self.bin.set_state(gst.STATE_NULL)
        self.bin.get_state()
        self.device.pipeline.remove(self.bin)
        self.bin = None
        print 'END remove', sink

    def get_pad(self):
        """
        Thread Information: called by gobject thread
        """
        return self.bin.get_pad('sink')

# create device for /dev/dvb/adapter0/frontend0
d = DVB(0, 0)

# ARD (Das Erste) in Bremen
ARD = {
    "frequency":482000000,
    "inversion": "AUTO",
    "bandwidth":str(8),
    "code-rate-hp":"2/3",
    "code-rate-lp":"1/2",
    "modulation":"QAM 16",
    "trans-mode":"8k",
    "guard":str(4),
    "hierarchy":"NONE"
}

ZDF = {
    "frequency":562000000,
    "inversion": "AUTO",
    "bandwidth":str(8),
    "code-rate-hp":"2/3",
    "code-rate-lp":"2/3",
    "modulation":"QAM 16",
    "trans-mode":"8k",
    "guard":str(4),
    "hierarchy":"NONE"
}

# tune to ARD in 0.5 seconds
kaa.OneShotTimer(d.tune, ARD).start(0.5)

# start recording 1 after 1 second from startup and stop 4 seconds later
sink = gst.parse_bin_from_description('queue ! filesink name=sink', True)
sink.get_by_name("sink").set_property('location', 'foo1.ts')
kaa.OneShotTimer(d.get_stream(160).append, sink).start(1.0)
kaa.OneShotTimer(d.get_stream(160).remove, sink).start(5.0)

# start recording 2 after 4 second from startup and stop 1 second later
sink = gst.element_factory_make('filesink')
sink.set_property('location', 'foo2.ts')
kaa.OneShotTimer(d.get_stream(160).append, sink).start(4.0)
kaa.OneShotTimer(d.get_stream(160).remove, sink).start(5.0)

# tune to ZDF after 6 seconds from startup
kaa.OneShotTimer(d.tune, ZDF).start(6)

# start recording 3 after 8 second from startup (ZDF) and stop 2 seconds later
sink = gst.element_factory_make('filesink')
sink.set_property('location', 'zdf.ts')
kaa.OneShotTimer(d.get_stream(514).append, sink).start(8.0)
kaa.OneShotTimer(d.get_stream(514).remove, sink).start(10.0)

# stop with C-c every time
kaa.main.run()
