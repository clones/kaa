#!/usr/bin/python
import pygst
pygst.require('0.10')
import gst
import gobject
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
        # tuning to ZDF (hardcoded values! change them!)
        self._tuner.set_property("frequency", 562000000)
        self._tuner.set_property("inversion", 2)
        self._tuner.set_property("bandwidth", 0)
        self._tuner.set_property("code-rate-high-prio", 2)
        self._tuner.set_property("code-rate-low-prio", 0)
        self._tuner.set_property("constellation", 1)
        self._tuner.set_property("transmission-mode", 1)
        self._tuner.set_property("guard-interval", 2)
        self._tuner.set_property("hierarchy", 0)

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



# test app logic

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


mapping = {}

def on_new_pad(dvb, pad):
    sink = mapping[pad.get_name()]
    pad.link(sink.get_pad('sink'))


# create gstreamer pipline
pipeline = gst.Pipeline()
pipeline.get_bus().add_watch(bus_event)

# create DVBCard object and add it
c = DVBCard()
c.connect("pad-added", on_new_pad)

pipeline.add(c)
pipeline.set_state(gst.STATE_PLAYING)



# now the testing starts by tuning
c.tune(None)


class TSFrame(object):
    def __init__(self, buffer):
        self.error = (ord(buffer[1]) & 0x80) >> 7
        self.pid = ((ord(buffer[1]) & 0x1F) << 8) | (ord(buffer[2]) & 0xFF)
        self.start = ord(buffer[1]) & 0x40
        adapt = (ord(buffer[3]) & 0x30) >> 4
        offset = 4
        if adapt & 0x01:
            offset += 1
        if adapt & 0x02:
            # meta info present
            adapt_len = ord(buffer[offset])
            offset += adapt_len + 1
        self.data = buffer[offset:]

        
class TableSink(gst.Element):

    _sinkpadtemplate = gst.PadTemplate ("sinkpadtemplate",
                                        gst.PAD_SINK,
                                        gst.PAD_ALWAYS,
                                        gst.caps_new_any())

    def __init__(self, *args):
        gst.Element.__init__(self)
        gst.info('creating sinkpad')
        self.sinkpad = gst.Pad(self._sinkpadtemplate, "sink")
        gst.info('adding sinkpad to self')
        self.add_pad(self.sinkpad)
        gst.info('setting chain/event functions')
        self.sinkpad.set_chain_function(self.chainfunc)
        self.sinkpad.set_event_function(self.eventfunc)
        self.buffer = {}
        self.finished = False
        self.parse_args = args
        
        
    def chainfunc(self, pad, buffer):
        if self.finished:
            return gst.FLOW_OK
        ts = TSFrame(buffer)
        if ts.error:
            # TS error bit set, ignore
            if not ts.pid in self.buffer:
                del self.buffer[ts.pid]
            return gst.FLOW_OK
        if not ts.start:
            # part of a stream
            if not ts.pid in self.buffer:
                return gst.FLOW_OK
            self.buffer[ts.pid].data += ts.data
            ts = self.buffer[ts.pid]
            del self.buffer[ts.pid]

        length = ((ord(ts.data[1]) & 0x0F) << 8) | ord(ts.data[2])
        if len(ts.data[3:]) < length:
            self.buffer[ts.pid] = ts
            return gst.FLOW_OK
        # table_id = 0
        # length = 1,2 (starting at 3)
        # transport_stream_id = 3,4
        # bla = 5
        # section_number = 6
        # last_section_number = 7
        data = [ ord(x) for x in ts.data[8:8+length-5-4] ]
        self.parse(ord(ts.data[0]), data, *self.parse_args)
        # now we need to unregister, but that does not work yet
        self.finished = True
        return gst.FLOW_OK


    def eventfunc(self, pad, event):
        print "%s event:%r" % (pad, event.type)
        return True



class PAT(TableSink):

    def parse(self, type_id, data):
        if not type_id == 0:
            print 'ERROR'
            return
        print 'Mapping info'
        pmts = []
        while data:
            num = (data[0] << 8) + data[1]
            pid = ((data[2] & 0x1F) << 8) + data[3]
            print '', num, pid
            data = data[4:]
            pmts.append((PMT(num, pid), pid))
        print
        for pmt, pid in pmts:
            pipeline.add(pmt)
            pmt.set_state(gst.STATE_PLAYING)
            mapping[str(pmt)] = pmt
            c.add_filter(str(pmt), pid)
            
            
class PMT(TableSink):

    def parse(self, type_id, data, num, pid):
        if not type_id == 2:
            print 'ERROR'
            return
        print
        print 'Info for', pid
        data = data[(((data[2] & 0x0f) << 8) | data[3]) + 4:]
        while data:
            pid = ((data[1] & 0x1f) << 8) | data[2]
            ES_info_len = ((data[3] & 0x0f) << 8) | data[4]
            if data[0] in (0x01, 0x02):
                print ' video', pid
            elif data[0] in (0x03, 0x04, 0x81):
                print ' audio', pid
            elif data[0] in (0x06,):
                # private data, can be ac3, teletext or subtitle

                def find_desc(id, data):
                    while len(data):
                        if data[0] == id:
                            return True
                        data = data[data[1] + 2:]
                    return False

                info = data[5:ES_info_len + 5]
                if find_desc(0x56, info):
                    print ' teletext', pid
                elif find_desc(0x59, info):
                    print ' subtitle', pid
                elif find_desc(0x6a, info):
                    # this does not work
                    print ' ac3', pid
                else:
                    print ' private', pid
            else:
                print ' unknown', pid
            data = data[ES_info_len + 5:]
        print

        
gobject.type_register(PAT)
gobject.type_register(PMT)

info = PAT()
pipeline.add(info)
info.set_state(gst.STATE_PLAYING)
mapping['info'] = info
c.add_filter('info', 0)

kaa.notifier.loop()
