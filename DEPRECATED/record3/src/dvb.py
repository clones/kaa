import pygst
pygst.require('0.10')
import gst
import gobject

import const
import device

class DVB(device.Device):

    def __init__(self, adapter):
        device.Device.__init__(self)
        # create pipeline
        self._pipeline = gst.Pipeline()
        self._pipeline.get_bus().add_watch(self._bus_event)
        self._dvbbin = gst.element_factory_make("dvbbasebin")
        self._dvbbin.set_property('adapter', adapter)
        self._dvbbin.connect("pad-added", self._pad_added)
        self._dvbbin.connect("pad-removed", self._pad_removed)
        self._pipeline.add(self._dvbbin)
        self._streams = {}
        self._tuning_data = None


    def add(self, channel, sink):
        # get tuning data and tune to specific frequency
        tuning_data, access_data = self.get_channel(channel)
        if self._tuning_data != tuning_data:
            # FIXME: does not work when already tuned!
            print '>>> tune to', tuning_data
            for var, value in tuning_data.items():
                self._dvbbin.set_property(var, value)
            self._tuning_data = tuning_data
        sid = str(access_data.get('sid'))

        # start pipeline
        if not self._streams:
            self._pipeline.set_state(gst.STATE_PLAYING);

        # create pipeline (tee) for channel if needed
        if not sid in self._streams:
            print 'create sid pipeline'
            tee = gst.element_factory_make('tee')
            tee.set_state(gst.STATE_PLAYING)
            self._pipeline.add(tee)
            self._streams[sid] = ( tee, [] )
            self._dvbbin.set_property('program-numbers', ':'.join(self._streams.keys()))

        # add sink to sid pipeline
        print 'start', sid, sink
        sink.set_state(gst.STATE_PLAYING)
        self._pipeline.add(sink)
        tee, streams = self._streams[sid]
        pad = tee.get_request_pad('src%d')
        pad.link(sink.get_pad('sink'))
        streams.append(sink)


    def remove(self, channel, sink):
        sid = str(self.get_channel(channel)[1].get('sid'))
        pad = sink.get_pad('sink').get_peer()
        tee, streams = self._streams[sid]
        # remove sink from pipeline and tee
        print 'remove', sink
        streams.remove(sink)
        sink.set_state(gst.STATE_NULL)
        self._pipeline.remove(sink)
        pad.unlink(sink.get_pad('sink'))
        tee.remove_pad(pad)
        if len(streams):
            return
        print 'last sink, remove sid', sid
        del self._streams[sid]
        self._dvbbin.set_property('program-numbers', ':'.join(self._streams.keys()))
        self._pipeline.remove(tee)
        tee.set_state(gst.STATE_NULL)
        if len(self._streams.keys()):
            return
        print 'last channel, stop dvbbin'
        self._dvbbin.set_state(gst.STATE_NULL)


    def _bus_event(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            return True
        if t == gst.MESSAGE_STATE_CHANGED:
            print message
            if message.parse_state_changed()[1] == gst.STATE_PLAYING:
                print '%s PLAYING' % message.src
            if message.parse_state_changed()[1] == gst.STATE_NULL:
                print '%s STOPPED' % message.src
            return True
        print message
        return True


    def _pad_added(self, bin, pad):
        sid = pad.get_name().split('_')[-1]
        print self._streams
        print 'PAD:', pad
        print 'PADNAME:',pad.get_name()
        print 'PADCAPS:',pad.get_caps()
        print 'SINK:', self._streams[sid]
        pad.link(self._streams[sid][0].get_pad('sink'))
        return True


    def _pad_removed(self, bin, pad):
        print 'STOP', pad, pad.get_peer()


class DVB_S(DVB):
    type = const.TYPE_DVB_S

    def _read_channels_conf_line(self, line):
        name, frequency, polarity, unknown, symbol_rate, \
              pid1, pid2, sid = line.strip().split(':')
        tuning_data = {
            'frequency': int(frequency) * 1000,
            'polarity': polarity,
            'symbol_rate': int(symbol_rate)
        }
        return name, tuning_data, dict(sid=sid)


class DVB_T(DVB):
    type = const.TYPE_DVB_T

    _BANDWIDTH = [ '8', '7', '6', 'AUTO' ]
    _GUARD = [ '32', '16', '8', '4', 'AUTO' ]
    _CODE = [ '1_2', '2_3', '3_4', '4_5', '5_6', '6_7', '7_8', '8_9', 'AUTO' ]
    _QUAM = [ 'QPSK', '16', '32', '64', '128', '256', 'AUTO' ]
    _TRANS = [ '2K', '8K', 'AUTO' ]
    _HIERARCHY = [ 'NONE', '1', '2', '4', 'AUTO' ]
    _INVERSION = [ 'OFF', 'ON', 'AUTO' ]

    def _read_channels_conf_line(self, line):
        name, frequency, inversion, bandwidth, code_rate_lq, code_rate_hq, \
              quam, transmission_mode, guard, hierarchy, \
              pid1, pid2, sid = line.strip().split(':')
        tuning_data = {
            'frequency': int(frequency),
            'bandwidth': self._BANDWIDTH.index(bandwidth.split('_')[1]),
            'guard': self._GUARD.index(guard.split('_')[-1]),
            'code-rate-lp': self._CODE.index(code_rate_lq[4:]),
            'code-rate-hp': self._CODE.index(code_rate_hq[4:]),\
            'modulation': self._QUAM.index(quam[4:]),
            'trans-mode': self._TRANS.index(transmission_mode.split('_')[-1]),
            'hierarchy': self._HIERARCHY.index(hierarchy.split('_')[-1]),
            'inversion': self._INVERSION.index(inversion.split('_')[-1])
        }
        return name, tuning_data, dict(sid=sid)
