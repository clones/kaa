import kaa
import gst

class DVB(object):

    def __init__(self, adapter, frontend):
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
        # needed for scanning
        # return
        if message.type == gst.MESSAGE_STATE_CHANGED:
            # print message
            dvbsrc = self.pipeline.get_by_name("dvbsrc")
            if message.src == dvbsrc:
                self.state = message.parse_state_changed()[1]
                print 'change state', self.state
                self.signals['state-change'].emit(self.state)
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
                    print 'found program %s on pid %s' % (sid, pmt)
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
                        # e.g. Das Erste with sid=160 tsid=3329
                        print name, sid, s["transport-stream-id"]
                return
            if message.structure.get_name() == 'pmt':
                s = message.structure
                # e.g. 160 (ARD)
                print 'pmt for', s['program-number']
                for stream in s['streams']:
                    print '', stream.keys()
                    print stream['pid'], stream['stream-type'], stream['descriptors']
                return
            if message.structure.get_name() == 'eit':
                # print message.structure.keys()
                return
            print 'Bus watch function for message %r' % message

    def _pad_added(self, element, pad):
        print 'START', pad
        sid = pad.get_name()[8:]
        if sid == '0':
            return
        pad.link(self.streams[sid].get_pad())
    
    def _pad_removed(self, bin, pad):
        print 'STOP', pad

    @kaa.coroutine()
    def tune(self, tuning_data):
        dvbsrc = self.pipeline.get_by_name("dvbsrc")
        if self.state in (gst.STATE_PLAYING, gst.STATE_PAUSED):
            print 'switch to gst.STATE_READY for tuning'
            dvbsrc.set_property("program-numbers", "")
            # FIXME: that may block for several seconds
            self.pipeline.set_state(gst.STATE_READY)
            while self.state in (gst.STATE_PLAYING, gst.STATE_PAUSED):
                yield kaa.InProgressSignals(self.signals, 'state-change')
            dvbsrc.set_property("program-numbers", "0")
        print 'tune'
        for key, value in tuning_data.items():
            dvbsrc.set_property(key, value)
        self.pipeline.set_state(gst.STATE_PLAYING)
        yield kaa.InProgressSignals(self.signals, 'state-change')


    def shutdown(self):
        self.pipeline.set_state(gst.STATE_NULL)


    def get_stream(self, sid):
        if not str(sid) in self.streams:
            self.streams[str(sid)] = Stream(self, sid=str(sid))
        return self.streams[str(sid)]
    

    def _stream_activate(self, stream):
        dvbsrc = self.pipeline.get_by_name("dvbsrc")
        programs = dvbsrc.get_property("program-numbers").split(':')
        if not stream.sid in programs:
            programs.append(stream.sid)
        dvbsrc.set_property("program-numbers", ':'.join(programs))


    def _stream_deactivate(self, stream):
        dvbsrc = self.pipeline.get_by_name("dvbsrc")
        programs = dvbsrc.get_property("program-numbers").split(':')
        if stream.sid in programs:
            programs.remove(stream.sid)
        programs = ':'.join(programs)
        if not programs:
            programs = ':'
        dvbsrc.set_property("program-numbers", programs)

        
class Stream(object):
    def __init__(self, device, **kwargs):
        self.device = device
        self.tee = None
        self.queue = None
        self.sinks = []
        for key, value in kwargs.items():
            setattr(self, key, value)
        
    def append(self, sink):
        if self.tee == None:
            print 'create stream'
            for attr in ('queue', 'tee'):
                setattr(self, attr, gst.element_factory_make(attr))
                getattr(self, attr).set_state(gst.STATE_PLAYING)
                self.device.pipeline.add(getattr(self, attr))
            self.queue.link(self.tee)
            self.device._stream_activate(self)
        print 'start', sink
        sink.set_state(gst.STATE_PLAYING)
        self.device.pipeline.add(sink)
        pad = self.tee.get_request_pad('src%d')
        pad.link(sink.get_pad('sink'))
        self.sinks.append(sink)

    def remove(self, sink):
        print 'remove', sink
        self.sinks.remove(sink)
        pad = sink.get_pad('sink').get_peer()
        pad.unlink(sink.get_pad('sink'))
        self.tee.remove_pad(pad)
        # sink.set_state(gst.STATE_NULL)
        if self.sinks:
            return
        print 'remove stream'
        for attr in ('queue', 'tee'):
            self.device.pipeline.remove(getattr(self, attr))
            getattr(self, attr).set_state(gst.STATE_NULL)
        print self.queue.get_pad('src').get_peer()
        print self.queue.get_pad('sink').get_peer()
        for attr in ('queue', 'tee'):
            setattr(self, attr, None)
        self.device._stream_deactivate(self)

    def get_pad(self):
        return self.queue.get_pad('sink')
    
kaa.main.select_notifier('generic')
kaa.gobject_set_threaded()

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

kaa.OneShotTimer(d.tune, ARD).start(0.5)
kaa.OneShotTimer(d.tune, ZDF).start(6)

sink = gst.element_factory_make('filesink')
sink.set_property('location', 'foo1.ts')
kaa.OneShotTimer(d.get_stream(160).append, sink).start(1.0)
kaa.OneShotTimer(d.get_stream(160).remove, sink).start(5.0)

sink = gst.element_factory_make('filesink')
sink.set_property('location', 'foo2.ts')
kaa.OneShotTimer(d.get_stream(160).append, sink).start(4.0)
kaa.OneShotTimer(d.get_stream(160).remove, sink).start(5.0)

sink = gst.element_factory_make('filesink')
sink.set_property('location', 'zdf.ts')
kaa.OneShotTimer(d.get_stream(514).append, sink).start(8.0)
kaa.OneShotTimer(d.get_stream(514).remove, sink).start(10.0)

kaa.main.run()
