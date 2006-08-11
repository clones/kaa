import sys
import os

import kaa.notifier

from kaa.player.skeleton import *
from kaa.player.utils import ChildProcess

class GStreamer(MediaPlayer):

    _instance_count = 0

    def __init__(self):
        super(GStreamer, self).__init__()
        self._instance_id = "kaa.gst-%d-%d" % (os.getpid(), GStreamer._instance_count)
        GStreamer._instance_count += 1

        self._stream_info = {}
        self._position = 0.0

        script = os.path.join(os.path.dirname(__file__), 'child.py')
        self.player = ChildProcess(self, script, str(self._instance_id))
        self.player.signals["completed"].connect_weak(self._exited)
        self.player.set_stop_command(notifier.WeakCallback(self._end_child))
        self.player.start()


    def _exited(self, exitcode):
        self._state = STATE_NOT_RUNNING
        self.signals["quit"].emit()


    def _end_child(self):
        self.player.die()


    # child handling
    
    def _child_set_status(self, pos):
        if self.get_state() not in (STATE_PAUSED, STATE_PLAYING):
            self.signals["start"].emit()
            self._state = STATE_PLAYING
        self._position = pos

        
    # public API
    
    def open(self, mrl):
        if mrl.find('://') == -1:
            mrl = 'file://' + mrl
        self._mrl = mrl
        self.signals["open"].emit()


    def play(self, video=True):
        if self.get_state() == STATE_PAUSED:
            self.player.play()
            return

        wid = None
        if self._window:
            wid = self._window.get_id()
        self.player.setup(wid=wid)

        self._position = 0.0
        self.player.open(self._mrl)
        self._state = STATE_OPENING


    def pause(self):
        self.player.pause()


    def pause_toggle(self):
        if self.get_state() == STATE_PLAYING:
            self.pause()
        else:
            self.play()


    def stop(self):
        self.player.stop()


    def get_info(self):
        return self._stream_info


    def osd_can_update(self):
        return False


    def get_position(self):
        return self._position


    def get_player_id(self):
        return "gstreamer"


    def nav_command(self, input):
        return False
    

    def is_in_menu(self):
        return False
