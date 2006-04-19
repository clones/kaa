import mplayer
import xine
from base import *

class Player(object):
    def __init__(self):
        self._player = None

        # We update the signals dict if it already exists in order to play 
        # friendly with multiple inheritance.
        if not hasattr(self, "signals"):
            self.signals = {}

        self.signals.update({
            "pause": notifier.Signal(),
            "play": notifier.Signal(),
            "pause_toggle": notifier.Signal(),
            "seek": notifier.Signal(),
            "open": notifier.Signal(),
            "start": notifier.Signal(),
            # Stream ended (either stopped by user or finished)
            "end": notifier.Signal(),
            "stream_changed": notifier.Signal(),
            "frame": notifier.Signal(), # CAP_CANVAS
            "osd_configure": notifier.Signal(),  # CAP_OSD
            # Process is about to die (shared memory will go away)
            "quit": notifier.Signal()
        })

    def open(self, mrl):
        if self._player and self.get_state() not in (STATE_NOT_RUNNING, STATE_IDLE):
            raise PlayerError('player is running')
        cls = get_player_class(mrl)
        if not cls:
            raise PlayerError("No supported player found to play %s", mrl)
        new_player = cls()
        if 1:#not self._player or new_player.get_player_id() != self._player.get_player_id():
            # Hook our signals to the player we're proxying for.
            for signal in self.signals.keys():
                new_player.signals[signal].connect_weak(self.signals[signal].emit)

            if self._player:
                # An active player already exists.  We need to kill it, in case
                # it's got something locked that our new instance needs.  We can't
                # start the new player until the old one is gone, so we construct
                # a state machine by using signals.
                self._player.signals["quit"].connect(new_player.open, mrl)
                self._player.die()
                self._player = new_player
                return

            self._player = new_player

        return self._player.open(mrl)


    def open(self, mrl, caps = None):
        cls = get_player_class(mrl = mrl, caps = caps)
        if not cls:
            raise PlayerError("No supported player found to play %s", mrl)

        if self._player != None:
            self._player.stop()
            if isinstance(self._player, cls):
                return self._player.open(mrl)

            # Continue open once our current player is dead.  We want to wait
            # before spawning the new one so that it releases the audio 
            # device.
            self._player.signals["quit"].connect_once(self._open, mrl, cls)
            self._player.die()
            return

        return self._open(mrl, cls)

    def _open(self, mrl, cls):
        self._player = cls()

        for signal in self.signals:
            if signal in self._player.signals:
                self._player.signals[signal].connect_weak(self.signals[signal].emit)

        self._player.open(mrl)


    def play(self, **kwargs):
        if not self._player:
            raise PlayerError, "Play called before open"
            return

        if self._open in self._player.signals["quit"]:
            # Waiting for old player to die.
            self.signals["open"].connect_once(self.play, **kwargs)
            return

        self._player.play(**kwargs)

    def stop(self):
        if self._player:
            self._player.stop()

    def pause(self):
        if self._player:
            self._player.pause()

    def pause_toggle(self):
        if self._player:
            self._player.pause_toggle()

    def seek_relative(self, offset):
        if self._player:
            self._player.seek_relative(offset)

    def seek_absolute(self, position):
        if self._player:
            self._player.seek_absolute(position)

    def seek_percentage(self, percent):
        if self._player:
            self._player.seek_percent(position)

    def get_position(self):
        if self._player:
            self._player.get_position()
        return 0.0

    def get_info(self):
        if self._player:
            self._player.get_info()
        return {}

    def nav_command(self, input):
        if self._player:
            self._player.nav_command(input)

    def is_in_menu(self):
        if self._player:
            return self._player.is_in_menu()
        return False
