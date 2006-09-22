import os
import sys
import fcntl

import pygst
pygst.require('0.10')
import gst

import kaa.notifier
kaa.notifier.init('gtk', x11=False)

from kaa.popcorn.utils import Player
from kaa.popcorn.ptypes import *

from gst_types import Status

class GStreamer(Player):

    def __init__(self, instance_id):
        Player.__init__(self)
        self._gst = None
        self._status_object = Status(self._send_status)
        self._status_last = None
        self._streaminfo = {}
        
    def get_status(self):
        return self._status_object.get_status()
    
    def set_status(self, status):
        return self._status_object.set_status(status)

    status = property(get_status, set_status, None, '')
    
    def _send_status(self):
        """
        Outputs stream status information.
        """
        if not self._gst:
            return

        pos = 0
        if self.status == Status.PLAYING:
            pos = float(self._gst.query_position(gst.FORMAT_TIME)[0] / 1000000) / 1000
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
            return True

        if msg.type == gst.MESSAGE_ERROR:
            for e in msg.parse_error():
                if not type(e) == gst.GError:
                    return True
                if e.domain.startswith('gst-stream-error') and \
                       e.code in (gst.STREAM_ERROR_NOT_IMPLEMENTED,
                                  gst.STREAM_ERROR_CODEC_NOT_FOUND,
                                  gst.STREAM_ERROR_TYPE_NOT_FOUND,
                                  gst.STREAM_ERROR_WRONG_TYPE):
                    # unable to play
                    self.status = Status.IDLE
                    return True
                if e.domain.startswith('gst-resource-error'):
                    self.status = Status.IDLE
                    return True
                # print e, e.code, e.domain
            return True
        if msg.type == gst.MESSAGE_TAG:
            taglist = msg.parse_tag()
            for key in taglist.keys():
                self._streaminfo[key] = taglist[key]
        return True
    
        
    # calls from parent
    
    def setup(self, wid):
        # create xv sink
        vo = gst.element_factory_make("xvimagesink", "vo")
        vo.set_xwindow_id(long(wid))
        vo.set_property('force-aspect-ratio', True)

        # now create the player and set the output
        self._gst = gst.element_factory_make("playbin", "player")
        self._gst.set_property('video-sink', vo)
        self._gst.get_bus().add_watch(self._gst_message)


    def open(self, uri):
        self._gst.set_property('uri', uri)
        self.status = Status.OPENING
        self._streaminfo = {}
        

    def play(self):
        self._gst.set_state(gst.STATE_PLAYING)


    def pause(self):
        self._gst.set_state(gst.STATE_PAUSED)


    def stop(self):
        self._gst.set_state(gst.STATE_NULL)
        self.status = Status.IDLE


    def die(self):
        sys.exit(0)


    def seek(self, value, type):
        pos = 0
        if type == SEEK_RELATIVE:
            pos = self._gst.query_position(gst.FORMAT_TIME)[0] + value * 1000000000
        if type == SEEK_ABSOLUTE:
            pos = value * 1000000000
        if type == SEEK_PERCENTAGE and 'duration' in self._streaminfo:
            pos = (self._streaminfo['duration'] / 100) * value
        self._gst.seek(1.0, gst.FORMAT_TIME,
                       gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
                       gst.SEEK_TYPE_SET, pos, gst.SEEK_TYPE_NONE, 0)
        
