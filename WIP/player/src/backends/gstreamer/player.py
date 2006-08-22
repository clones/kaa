import sys
import os

import kaa.notifier

from kaa.player.backends.base import MediaPlayer
from kaa.player.ptypes import *
from kaa.player.utils import ChildProcess

from gst_types import Status

class GStreamer(MediaPlayer):

    _instance_count = 0

    def __init__(self):
        super(GStreamer, self).__init__()
        self._instance_id = "kaa.gst-%d-%d" % (os.getpid(), GStreamer._instance_count)
        GStreamer._instance_count += 1

        self._stream_info = {}
        self._position = 0.0
        self._state = STATE_NOT_RUNNING


    def _span(self):
        script = os.path.join(os.path.dirname(__file__), 'child.py')
        self._gst = ChildProcess(self, script, str(self._instance_id))
        self._gst.signals["completed"].connect_weak(self._exited)
        self._gst.set_stop_command(kaa.notifier.WeakCallback(self._end_child))
        self._gst.start()
        self._state = STATE_IDLE


    def _exited(self, exitcode):
        self._state = STATE_NOT_RUNNING


    def _end_child(self):
        self._state = STATE_SHUTDOWN
        self._gst.die()


    # child handling
    
    def _child_set_status(self, status, pos):
        if status == Status.PLAYING:
            if not self.get_state() in (STATE_PLAYING, STATE_PAUSED):
                self._state = STATE_PLAYING
            self._position = pos
            return True
        if status == Status.IDLE:
            self._state = STATE_IDLE
        self._position = 0
        

    # public API
    
    def open(self, mrl):
        if mrl.find('://') == -1:
            mrl = 'file://' + mrl
        self._mrl = mrl
        if self._state == STATE_NOT_RUNNING:
            self._span()
        self._position = 0.0


    def play(self):
        """
        Start playing. If playback is paused, resume. If not wait
        async until either the playing has started or an error
        occurred.
        """
        wid = None
        if self._window:
            wid = self._window.get_id()
        self._gst.setup(wid=wid)
        self._gst.open(self._mrl)
        self._gst.play()
        self._state = STATE_OPENING
        return


    def pause(self):
        self._gst.pause()
        self._state = STATE_PAUSED


    def resume(self):
        self._gst.play()
        self._state = STATE_PLAYING

        
    def stop(self):
        self._gst.stop()


    def die(self):
        self.stop()
        self._gst.die()
        self._state = STATE_SHUTDOWN


    def get_info(self):
        return self._stream_info


    def osd_can_update(self):
        return False


    def get_position(self):
        return self._position


    def seek(self, value, type):
        self._gst.seek(value, type)


    def nav_command(self, input):
        return False
    

    def is_in_menu(self):
        return False
