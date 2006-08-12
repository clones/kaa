import kaa.notifier
import threading, re, os, stat, sets

from ptypes import *
from utils import parse_mrl

class PlayerError(Exception):
    pass

class PlayerCapError(PlayerError):
    pass

class MediaPlayer(object):
    """
    Base class for players
    """

    def __init__(self):
        self.signals = {
            "pause": kaa.notifier.Signal(),
            "play": kaa.notifier.Signal(),
            "pause_toggle": kaa.notifier.Signal(),
            "seek": kaa.notifier.Signal(),
            "open": kaa.notifier.Signal(),
            "start": kaa.notifier.Signal(),
            "failed": kaa.notifier.Signal(),
            # Stream ended (either stopped by user or finished)
            "end": kaa.notifier.Signal(),
            "stream_changed": kaa.notifier.Signal(),
            "frame": kaa.notifier.Signal(), # CAP_CANVAS
            "osd_configure": kaa.notifier.Signal(),  # CAP_OSD
            # Process is about to die (shared memory will go away)
            "quit": kaa.notifier.Signal()
        }

        self._state_object = STATE_NOT_RUNNING
        self._window = None
        self._size = None


    def get_capabilities(self):
        return self._player_caps        # filled by generic

    def get_supported_schemes(self):
        return self._player_schemes     # filled by generic

    def has_capability(self, cap):
        supported_caps = self.get_capabilities()
        if type(cap) not in (list, tuple):
            return cap in supported_caps

        return sets.Set(cap).issubset(sets.Set(supported_caps))

    def get_state(self):
        return self._state_object

    def _set_state(self, state):
        # handle state changes
        if self._state == STATE_OPENING and \
               state in (STATE_IDLE, STATE_NOT_RUNNING):
            self.signals["failed"].emit()
        if self._state == STATE_OPENING and \
               state in (STATE_PLAYING, STATE_PAUSED):
            self.signals["start"].emit()
        if self._state in (STATE_PLAYING, STATE_PAUSED) and \
               state in (STATE_IDLE, STATE_NOT_RUNNING):
            self.signals["end"].emit()

        # save new state
        self._state_object = state

    _state = property(get_state, _set_state, None, '')
    
    def get_window(self):
        return self._window

    def is_paused(self):
        return self.state == STATE_PAUSED

    def set_window(self, window):
        # Caller can pass his own X11Window here.  If it's None, it will
        # get created in the play() call.
        if not self.has_capability(CAP_VIDEO):
            raise PlayerCapError, "Player doesn't have CAP_VIDEO"
        self._window = window
        
    def set_size(self, size):
        if not self.has_capability(CAP_VIDEO):
            raise PlayerCapError, "Player doesn't have CAP_VIDEO"
        self._size = size


    #
    # Methods to be implemented by subclasses.
    #

    def open(self, mrl):
        pass

    def play(self):
        pass

    def pause(self):
        pass

    def pause_toggle(self):
        pass

    def stop(self):
        pass

    def seek_relative(self, offset):
        pass

    def seek_absolute(self, position):
        pass

    def seek_percentage(self, percent):
        pass

    def get_position(self):
        pass

    def get_info(self):
        """
        Returns info about the currently playing stream, or the file that
        has just been opened.
        """
        pass

    def nav_command(self, input):
        return input in (
            "up", "down", "left", "right", "select", "next", "previous",
            "angle_prev", "angle_next", "menu1", "menu2", "menu3", "menu4"
            "menu5", "menu6", "menu7", "0", "1", "2", "3", "4", "5", "6" "7",
            "8", "9")

    def is_in_menu(self):
        return False

    # For CAP_OSD

    def osd_update(self, alpha = None, visible = None, invalid_regions = None):
        pass

    def osd_can_update(self):
        pass

    # For CAP_CANVAS
    
    def set_frame_output_mode(self, vo = None, notify = None, size = None):
        """
        If vo is True, render video to the vo driver's video window.  If
        False, suppress.  If notify is True, emit "frame" signal when new 
        frame available.  size is a 2-tuple containing the target size of the
        frame as given to the "frame" signal callback.  If any are None, do 
        not alter the status since last call.
        """
        pass

    def unlock_frame_buffer(self):
        """
        Unlocks the frame buffer provided by "frame" signal.
        """
        pass

    def die(self):
        """
        Kills the player.  No more files may be played once die() is called.
        """
        pass
