import sys
import os

import kaa.notifier

from kaa.player.skeleton import MediaPlayer
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
        self.player = ChildProcess(self, script, str(self._instance_id))
        self.player.signals["completed"].connect_weak(self._exited)
        self.player.set_stop_command(kaa.notifier.WeakCallback(self._end_child))
        self.player.start()
        self._state = STATE_IDLE
        self._stopping = False

    def _exited(self, exitcode):
        self._state = STATE_NOT_RUNNING
        self.signals["quit"].emit()


    def _end_child(self):
        self.player.die()


    # child handling
    
    def _child_set_status(self, status, pos):
        if status == Status.PLAYING:
            if not self.get_state() in (STATE_PLAYING, STATE_PAUSED):
                self._state = STATE_PLAYING
            self._position = pos
            return True
        if status == Status.IDLE:
            if self._stopping and self._state == STATE_OPENING:
                self._stopping = False
            else:
                self._state = STATE_IDLE
        self._position = 0
        

    # public API
    
    def open(self, mrl):
        if mrl.find('://') == -1:
            mrl = 'file://' + mrl
        self._mrl = mrl
        self.signals["open"].emit()
        if self._state == STATE_NOT_RUNNING:
            self._span()


    def play(self, video=True):
        """
        Start playing. If playback is paused, resume. If not wait
        async until either the playing has started or an error
        occurred.
        """
        if self.get_state() == STATE_PAUSED:
            self.player.play()
            return True

        wid = None
        if self._window:
            wid = self._window.get_id()
        self.player.setup(wid=wid)

        self._position = 0.0

        self.player.open(self._mrl)
        self._state = STATE_OPENING
        return


    def pause(self):
        self.player.pause()


    def pause_toggle(self):
        if self.get_state() == STATE_PLAYING:
            self.pause()
        else:
            self.play()


    def stop(self):
        self._stopping = True
        self.player.stop()
        self._state = STATE_IDLE


    def die(self):
        self.stop()
        self.player.die()
        self._state = STATE_NOT_RUNNING


    def get_info(self):
        return self._stream_info


    def osd_can_update(self):
        return False


    def get_position(self):
        return self._position


    def nav_command(self, input):
        return False
    

    def is_in_menu(self):
        return False
