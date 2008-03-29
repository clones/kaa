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
import gst

class TuneExeception(Exception):
    pass

class DVB(object):

    def __init__(self, adapter, frontend):
        """
        Thread Information: created by the main thread
        """
        self.signals = kaa.Signals('state-change', 'lock', 'channels')
        self.adapter = adapter
        self.frontend = frontend
        self.type = None
        self.streams = {}
        self.channels = {}
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

    def _parse_nit(self, nit):
        """
        Parse network information
        Thread Information: called by bus_watch_func from main thread
        """
        name = nit['network-id']
        actual = nit['actual-network']
        if nit.has_key('network-name'):
            name = nit['network-name']
        transports = nit['transports']
        for transport in transports:
            tsid = transport['transport-stream-id']
            if not transport.has_key('delivery'):
                continue
            # delivery information to get the real tuning_data
            delivery = transport['delivery']
            modulation = delivery["constellation"]
            if modulation == "reserved":
                modulation = "QAM 64"
            hierarchy = delivery['hierarchy']
            if hierarchy == 0:
                hierarchy = "NONE"
            transmission = delivery['transmission-mode']
            if transmission == 'reserved':
                # FIXME: how to handle this?
                transmission = '8k'
            # FIXME: this is DVB-T only yet
            tuning_data = {
                "frequency": delivery['frequency'],
                "inversion": 'AUTO',
                "bandwidth": str(delivery['bandwidth']),
                "code-rate-hp": delivery['code-rate-hp'],
                "code-rate-lp": delivery['code-rate-hp'],
                "modulation": modulation,
                "trans-mode": delivery['transmission-mode'],
                "guard": str(delivery['guard-interval']),
                "hierarchy": hierarchy
            }
            # FIXME: wait for this on scanning. It may take a while
            # until it arrives, but it gives us the correct tuning_data
            # Note: it may not arrive for bad channels. Timeout?
            print name, tuning_data
        
    @kaa.threaded(kaa.MAINTHREAD)
    def bus_watch_func(self, bus, message):
        """
        Thread Information: called by gobject but forced into main thread
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
                self._parse_nit(message.structure)
                return
            if message.structure.get_name() == 'pat':
                programs = message.structure['programs']
                for p in programs:
                    # e.g. sid 160 (Das Erste) on pmt 260
                    # This information is not needed in kaa.record, dvbbasebin
                    # handles this, only the sid is needed.
                    sid = p['program-number']
                    pmt = p['pid']
                return
            if message.structure.get_name() == 'sdt':
                # channel listing
                s = message.structure
                if s["actual-transport-stream"]:
                    self.channels = []
                    for service in s["services"]:
                        name = service.get_name()
                        sid = int(name[8:])
                        if service.has_key("name"):
                            name = service["name"]
                        self.channels.append((name, sid))
                    # Note: it may not arrive for bad channels. Timeout?
                    self.signals['channels'].emit(self.channels)
                return
            if message.structure.get_name() == 'pmt':
                s = message.structure
                # e.g. 160 (ARD), no idea how to read the descriptor or if this
                # information is needed at all for kaa.record
                # print 'pmt for', s['program-number']
                # for stream in s['streams']:
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
        print 'set ready for tuning'
        element = self.pipeline
        if dvbsrc.get_state()[1] == gst.STATE_PLAYING:
            element = dvbsrc
        # XXX This sometimes blocks on re-tuning. Sometimes it is non blocking,
        # XXX sometimes it blocks for 10 or 20 seconds and sometimes it blocks
        # XXX over a minute
        element.set_state(gst.STATE_READY)
        self.channels = None
        print 'tune'
        for key, value in tuning_data.items():
            dvbsrc.set_property(key, value)
        element.set_state(gst.STATE_PLAYING)
        (statereturn, state, pending) = dvbsrc.get_state()
        if statereturn == gst.STATE_CHANGE_FAILURE:
            raise TuneExeception('no lock')


    def get_stream(self, sid):
        """
        Thread Information: called by main thread
        """
        if not str(sid) in self.streams:
            self.streams[str(sid)] = Stream(self, sid=str(sid))
        return self.streams[str(sid)]


    def _stream_activate(self, stream):
        """
        Thread Information: called by Stream object in gobject thread
        """
        dvbsrc = self.pipeline.get_by_name("dvbsrc")
        programs = dvbsrc.get_property("program-numbers").split(':')
        if not stream.sid in programs:
            programs.append(stream.sid)
        dvbsrc.set_property("program-numbers", ':'.join(programs))


    def _stream_deactivate(self, stream):
        """
        Thread Information: called by Stream object in gobject thread
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
