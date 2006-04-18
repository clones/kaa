import xine
import mplayer
from base import *

class Player(object):
    def __init__(self):
        object.__setattr__(self, 'player', None)

        object.__setattr__(self, 'signals',  {
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
        if self.player and self.player.get_state() \
               not in (STATE_NOT_RUNNING, STATE_IDLE):
            raise PlayerError('player is running')
        cls = get_player_class(mrl)
        if not cls:
            raise PlayerError("No supported player found to play %s", mrl)
        # if not self.player or cls.get_player_id() != self.player.get_player_id():
        object.__setattr__(self, 'player', cls())
        for signal in self.signals.keys():
            self.player.signals[signal].connect_weak(self.signals[signal].emit)
        return self.player.open(mrl)
        
    def __getattr__(self, attr):
        if not self.player:
            raise PlayerError("No mrl loaded")
        return getattr(self.player, attr)
    
    def __setattr__(self, attr, value):
        if not self.player:
            raise PlayerError("No mrl loaded")
        return setattr(self.player, attr, value)
