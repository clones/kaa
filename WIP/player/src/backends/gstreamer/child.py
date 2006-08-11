import os
import sys
import fcntl

import pygst
pygst.require('0.10')
import gst

import kaa.notifier

from ipc import Player

kaa.notifier.init('gtk', x11=False)

class GStreamer(Player):

    def __init__(self, instance_id):
        Player.__init__(self)
        self.player = None

        self._status = kaa.notifier.WeakTimer(self._set_status)
        self._status.start(0.1)
        self._status_last = None
        
        
    def _set_status(self):
        """
        Outputs stream status information.
        """
        if not self.player:
            return

        pos = float(self.player.query_position(gst.FORMAT_TIME)[0] / 1000000) / 1000
        if pos != self._status_last:
            self._status_last = pos
            self.parent.set_status(pos)


    def _gst_message(self, bus, msg):
        # do something clever here
        # print msg
        return True
    
        
    # calls from parent
    
    def setup(self, wid):
        # create xv sink
        vo = gst.element_factory_make("xvimagesink", "vo")
        vo.set_xwindow_id(long(wid))
        vo.set_property('force-aspect-ratio', True)

        # now create the player and set the output
        self.player = gst.element_factory_make("playbin", "player")
        self.player.set_property('video-sink', vo)
        self.player.get_bus().add_watch(self._gst_message)


    def open(self, uri):
        self.player.set_property('uri', uri)
        self.player.set_state(gst.STATE_PLAYING)
        print 'start', uri


    def stop(self):
        pass


    def die(self):
        self._handle_command_stop()
        sys.exit(0)


player = GStreamer(sys.argv[1])
kaa.notifier.loop()
