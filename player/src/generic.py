import xine
import mplayer
from base import *

class Player(object):
    def __init__(self):
        object.__setattr__(self, 'player', None)

    def open(self, mrl):
        if self.player:
            self.player.stop()
            self.player = None
        cls = get_player_class(mrl)
        if not cls:
            raise PlayerError("No supported player found to play %s", mrl)
        object.__setattr__(self, 'player', cls())
        return self.player.open(mrl)
        
    def __getattr__(self, attr):
        if not self.player:
            raise PlayerError("No mrl loaded")
        return getattr(self.player, attr)
    
    def __setattr__(self, attr, value):
        if not self.player:
            raise PlayerError("No mrl loaded")
        return setattr(self.player, attr, value)
