import sys
import os

import kaa.notifier

from kaa.player.skeleton import *
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

        script = os.path.join(os.path.dirname(__file__), 'child.py')
        self.player = ChildProcess(self, script, str(self._instance_id))
        self.player.signals["completed"].connect_weak(self._exited)
        self.player.set_stop_command(notifier.WeakCallback(self._end_child))
        self.player.start()
        self._play_wait = None
        

    def _exited(self, exitcode):
        self._state = STATE_NOT_RUNNING
        self.signals["quit"].emit()


    def _end_child(self):
        self.player.die()


    # child handling
    
    def _child_set_status(self, status, pos):
        if status == Status.PLAYING:
            if self._play_wait:
                self._play_wait.finished(True)
            self._position = pos
            return True

        self._position = 0
        if status == Status.IDLE and self._play_wait:
            self._play_wait.finished(False)

        
    # public API
    
    def open(self, mrl):
        if mrl.find('://') == -1:
            mrl = 'file://' + mrl
        self._mrl = mrl
        self.signals["open"].emit()


    @kaa.notifier.yield_execution()
    def play(self, video=True):
        """
        Start playing. If playback is paused, resume. If not wait
        async until either the playing has started or an error
        occurred.
        """
        if self.get_state() == STATE_PAUSED:
            self.player.play()
            yield True

        wid = None
        if self._window:
            wid = self._window.get_id()
        self.player.setup(wid=wid)

        self._position = 0.0
        self.player.open(self._mrl)
        self._state = STATE_OPENING

        # wait for child to start
        self._play_wait = kaa.notifier.InProgress()
        yield self._play_wait
        playing = self._play_wait()
        self._play_wait = None

        if not playing:
            self._state = STATE_IDLE
            print 'Unable to play the stream'
            yield False
            
        self.signals["start"].emit()
        self._state = STATE_PLAYING
        yield True


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


    def nav_command(self, input):
        return False
    

    def is_in_menu(self):
        return False
