from kaa import notifier, display
import threading, re

CAP_NONE  = 0x00
CAP_VIDEO = 0x01
CAP_AUDIO = 0x02
CAP_OSD   = 0x04
CAP_CANVAS = 0x08
CAP_DVD = 0x10
CAP_DVD_MENUS = 0x20
CAP_DYNAMIC_FILTERS = 0x40
CAP_VARIABLE_SPEED = 0x80
CAP_VISUALIZATION = 0x100
CAP_DEINTERLACE = 0x200

STATE_NOT_RUNNING = 0
STATE_IDLE = 1
STATE_OPENING = 2
STATE_PLAYING = 3
STATE_PAUSED = 4

_players = {}

def register_player(player_id, cls, get_caps_callback):
    assert(issubclass(cls, MediaPlayer))
    if player_id in _players:
        raise ValueError, "Player '%s' already registered" % name

    # FIXME: could block, so should call this asynchronously
    caps, schemes = get_caps_callback()
    _players[player_id] = {
        "class": cls,
        "caps": caps,
        "schemes": schemes
    }


def get_player(player = None, mrl = None, caps = None):
    if player == mrl == caps == None:
        # FIXME: return default player?
        return _players.values()[0]["class"]()

    if player != None and player in _players:
        return _players[player]["class"]()

    if mrl != None:
        scheme = re.search("^(\S+)(?:)", mrl).group(1)
        for player in _players.values():
            if scheme in player["schemes"]:
                return player["class"]()

    if caps != None:
        for player in _players.values():
            if player["caps"] & caps:
                return player["class"]()



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
            "pause": notifier.Signal(),
            "play": notifier.Signal(),
            "pause_toggle": notifier.Signal(),
            "seek": notifier.Signal(),
            "open": notifier.Signal(),
            "start": notifier.Signal(),
            "end": notifier.Signal(),
            "stream_changed": notifier.Signal(),
            "frame": notifier.Signal(), # CAP_CANVAS
            "osd_configure": notifier.Signal()  # CAP_OSD
        }

        self._state = STATE_NOT_RUNNING
        self._window = None
        self._size = None


    def get_capabilities(self):
        return _players[self.get_player_id()]["caps"]

    def has_capability(self, cap):
        return self.get_capabilities() & cap != 0

    def get_state(self):
        return self._state

    def get_window(self):
        return self._window

    def is_paused(self):
        return self.get_state() == STATE_PAUSED

    def set_window(self, window):
        # Caller can pass his own X11Window here.  If it's None, it will
        # get created in the play() call.
        if not self.has_capability(CAP_VIDEO):
            raise PlayerCapError, "Player doesn't have CAP_VIDEO"

        assert(type(window) == display.X11Window)
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
        pass

    def get_player_id(self):
        return None

    def nav_command(self, input):
        pass


    # For CAP_OSD

    def osd_update(self, alpha = None, visible = None, invalid_regions = None):
        pass

    def osd_can_update(self):
        pass

