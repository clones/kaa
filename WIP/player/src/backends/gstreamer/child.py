import os
import sys
import fcntl

import pygst
pygst.require('0.10')
import gst

import kaa.notifier
kaa.notifier.init('gtk', x11=False)

from kaa.player.utils import Player

from gst_types import Status

class GStreamer(Player):

    def __init__(self, instance_id):
        Player.__init__(self)
        self.player = None
        self._status_object = Status(self._send_status)
        self._status_last = None


    def get_status(self):
        return self._status_object.get_status()
    
    def set_status(self, status):
        return self._status_object.set_status(status)

    status = property(get_status, set_status, None, '')
    
    def _send_status(self):
        """
        Outputs stream status information.
        """
        if not self.player:
            return

        pos = float(self.player.query_position(gst.FORMAT_TIME)[0] / 1000000) / 1000
        current = self.status, pos
        
        if current != self._status_last:
            self._status_last = current
            self.parent.set_status(*current)


    def _gst_message(self, bus, msg):
        # do something clever here
        if msg.type == gst.MESSAGE_STATE_CHANGED:
            old, new, pending = msg.parse_state_changed()
            if new == gst.STATE_PLAYING:
                self.status = Status.PLAYING
            # print 'state', new
            return True
        if msg.type == gst.MESSAGE_ERROR:
            for e in msg.parse_error():
                if not type(e) == gst.GError:
                    return True
                if e.domain.startswith('gst-stream-error') and \
                       e.code in (gst.STREAM_ERROR_CODEC_NOT_FOUND,
                                  gst.STREAM_ERROR_TYPE_NOT_FOUND,
                                  gst.STREAM_ERROR_WRONG_TYPE):
                    # unable to play
                    self.status = Status.IDLE
                    return True
                # print e, e.code, e.domain
            return True
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
        self.status = Status.OPENING
        print 'start', uri


    def stop(self):
        pass


    def die(self):
        self._handle_command_stop()
        sys.exit(0)


player = GStreamer(sys.argv[1])
kaa.notifier.loop()
