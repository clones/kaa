import pygst
pygst.require('0.10')
import gst

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
