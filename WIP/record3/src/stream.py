import pygst
pygst.require('0.10')
import gst

class Stream(object):

    def __init__(self, device, channel, sink):
        self._device = device
        self._channel = channel
        self._sink = sink

    def start(self):
        self._device.add(self._channel, self._sink)

    def stop(self):
        self._device.remove(self._channel, self._sink)
        self._device = None
        self._sink = None


class Recording(Stream):

    def __init__(self, device, channel, filename):
        sink = gst.element_factory_make('filesink')
        sink.set_property('location', filename)
        super(Recording,self).__init__(device, channel, sink)
