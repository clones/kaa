#!/usr/bin/python
import pygst
pygst.require('0.10')
import gst
import gobject
import sys
import time
import gc

# import kaa.notifier and set mainloop to glib
import kaa.notifier
kaa.notifier.init('gtk', x11=False)

# import kaa.record2 for the dvbtuner module
import kaa.record2

class DVBsrc(gst.Bin):
    def __init__(self):
        gst.Bin.__init__(self, 'dvbsrc_%d')
        self._src = gst.element_factory_make("fdsrc")
        self._tuner = gst.element_factory_make("dvbtuner")
        self._tuner.set_property('debug-output', True)
        self._queue = gst.element_factory_make("queue")
        self._splitter = gst.element_factory_make("tssplitter")
        self._splitter.connect("pad-added", self._on_new_pad)
        self.add(self._src, self._queue, self._splitter)
        gst.element_link_many(self._src, self._queue, self._splitter)
        self._pids = []
        self._newpad = None
        self._nextid = 0
        

    def set_property(self, prop, value):
        if prop == 'adapter':
            self._tuner.set_property('adapter', value)
            self._dvr = open('/dev/dvb/adapter%s/dvr0' % value)
            return self._src.set_property('fd', self._dvr.fileno())

        if prop == 'channel':
            channel = value
            frontendtype = self._tuner.get_property('frontendtype')
            if frontendtype == 0:
                # TODO FIXME broken --> fixme
                DVBS
            elif frontendtype == 1:
                # TODO FIXME broken --> fixme
                DVBC
            elif frontendtype == 2:
                # TODO FIXME I have to fix parser and tuner! -
                # they should use the same keywords
                channel.config['constellation'] = channel.config['modulation']
            
                for cfgitem in [ 'frequency', 'inversion', 'bandwidth',
                                 'code-rate-high-prio', 'code-rate-low-prio',
                                 'constellation', 'transmission-mode',
                                 'guard-interval', 'hierarchy' ]:
                    print '%s ==> %s' % (cfgitem, channel.config[ cfgitem ])
                    self._tuner.set_property( cfgitem, channel.config[ cfgitem ] )
                      
            elif frontendtype == 3:
                # TODO FIXME broken --> fixme
                ATSC
            else:
                print 'OH NO! Please fix this code!'
            
            # tune to channel
            self._tuner.emit("tune")
            return True

        raise AttributeError


    def _on_new_pad(self, splitter, pad):
        self._newpad = gst.GhostPad(pad.get_name(), pad)
        self.add_pad(self._newpad)


    def get_request_pad(self, *pids):
        for pid in pids:
            if not pid in self._pids:
                self._tuner.emit("add-pid", pid)
                self._pids.append(pid)
        pidstr = ','.join([str(p) for p in pids])
        # FIXME: self._splitter.get_request_pad would be the way to go
        # To do that, tssplitter has to provide a release_pad function.
        # For some reasons I could not get this working, so it is still
        # this ugly hack. See gsttee.c how stuff like that should work.
        self._splitter.emit("set-filter", 'dvbpid_%s' % self._nextid, pidstr)
        self._nextid += 1
        return self._newpad


    def remove_pad(self, pad):
        # TODO: remove pids from tuner
        # FIXME: that results in GStreamer-CRITICAL
        self._splitter.emit("remove-filter", pad.get_target().get_name())
        gst.Bin.remove_pad(self, pad)


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


if len(sys.argv) < 3:
    print 'syntax: %s <channels.conf> <channelname>' % sys.argv[0]
    sys.exit()

channelsconf = kaa.record2.ConfigFile( sys.argv[1] )
channel = channelsconf.get_channel( sys.argv[2] )
if not channel:
    print 'cannot find channel', sys.argv[2]
    sys.exit()

# create gstreamer pipline
pipeline = gst.Pipeline()
pipeline.get_bus().add_watch(bus_event)

# create DVBsrc object and add it
dvb = DVBsrc()
# FIXME: it would be nice to do
# gst.element_factory_make("dvbsrc")

dvb.set_property('adapter', 0)
dvb.set_property('channel', channel)

pipeline.add(dvb)
pipeline.set_state(gst.STATE_PLAYING)


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

    def __init__(self, dvbsrc, *args):
        gst.Element.__init__(self)
        gst.info('creating sinkpad')
        pad = gst.Pad(self._sinkpadtemplate, "sink")
        pad.set_chain_function(self.chainfunc)
        self.add_pad(pad)
        self.buffer = {}
        self.parse_args = args
        self.dvbsrc = dvbsrc
        
        
    def chainfunc(self, pad, buffer):
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
        self.delete()
        return gst.FLOW_OK


    def delete(self):
        pad = self.get_pad('sink')
        peer = pad.get_peer()
        peer.unlink(pad)
        self.dvbsrc.remove_pad(peer)
        self.unparent()
        self.remove_pad(pad)
        self.set_state(gst.STATE_NULL)



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
            pmts.append((PMT(self.dvbsrc, num, pid), pid))
        print
        for pmt, pid in pmts:
            pipeline.add(pmt)
            pmt.set_state(gst.STATE_PLAYING)
            self.dvbsrc.get_request_pad(pid).link(pmt.get_pad('sink'))
            
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


def gc_check():
    gc.collect()
    for g in gc.garbage:
        print 'oops', g

gobject.type_register(PAT)
gobject.type_register(PMT)

info = PAT(dvb)
pipeline.add(info)
info.set_state(gst.STATE_PLAYING)

dvb.get_request_pad(0).link(info.get_pad('sink'))

kaa.notifier.Timer(gc_check).start(1)
kaa.notifier.loop()
