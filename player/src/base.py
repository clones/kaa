from kaa import notifier, display
import threading, re, os, stat, sets

CAP_NONE  = 0
CAP_VIDEO = 1
CAP_AUDIO = 2
CAP_OSD   = 3
CAP_CANVAS = 3
CAP_DVD = 4
CAP_DVD_MENUS = 5
CAP_DYNAMIC_FILTERS = 6
CAP_VARIABLE_SPEED = 7
CAP_VISUALIZATION = 8
CAP_DEINTERLACE = 9

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

    # FIXME: could block, so should call this in a thread
    caps, schemes, exts = get_caps_callback()
    _players[player_id] = {
        "class": cls,
        "caps": caps,
        "schemes": schemes,
        # Prefer this player for these extensions.  (It's not a list of
        # all supported extensions.)
        "extensions": exts
    }


def parse_mrl(mrl):
    """
    Parses a mrl, returning a 2-tuple (scheme, path) where scheme is the mrl
    scheme such as file, dvd, fifo, udp, etc., and path is the whatever
    follows the mrl scheme.  If no mrl scheme is specified in 'mrl', it
    attempts to make an intelligent choice.
    """
    scheme, path = re.search("^(\w{,4}:)?(.*)", mrl).groups()
    if not scheme:
        scheme = "file"
        try:
            stat_info = os.stat(path)
        except OSError:
            return scheme, path

        if stat_info[stat.ST_MODE] & stat.S_IFIFO:
            scheme = "fifo"
        else:
            f = open(path)
            f.seek(32768, 0)
            b = f.read(60000)
            if b.find("UDF") != -1:
                b = f.read(550000)
                if b.find('OSTA UDF Compliant') != -1 or b.find("VIDEO_TS") != -1:
                    scheme = "dvd"
    else:
        scheme = scheme[:-1]
    return scheme, path



def get_player_class(mrl = None, caps = None, player = None, exclude = None):
    """
    Searches the registered players for the most capable player given the mrl
    or required capabilities.  A specific player can be returned by specifying
    the player id.  If exclude is specified, it is a name (or list of names)
    of players to skip (in case one or more players are known not to work with
    the given mrl).  The player's class object is returned if a suitable
    player is found, otherwise None.
    """
    if player == mrl == caps == None:
        # FIXME: return default player?
        return _players.values()[0]["class"]

    if player != None and player in _players:
        return _players[player]["class"]

    if mrl != None:
        scheme, path = parse_mrl(mrl)
        ext = os.path.splitext(path)[1]
        if ext:
            ext = ext[1:]  # Eat leading '.'

    if caps != None and type(caps) not in (tuple, list):
        caps = (caps,)
    if exclude != None and type(exclude) not in (tuple, list):
        exclude  = (exclude,)


    choice = None
    for player_id, player in _players.items():
        if mrl != None and scheme not in player["schemes"]:
            # mrl scheme not supported by this player
            continue
        if exclude and player_id in exclude:
            continue
        if caps != None:
            if not sets.Set(caps).issubset(sets.Set(player["caps"])):
                # Requested capabilities not present.
                continue
            if scheme == "dvd" and choice and CAP_DVD_MENUS in choice["caps"] and \
               CAP_DVD_MENUS not in player["caps"]:
                # If the mrl is dvd, make sure we prefer the player that
                # supports CAP_DVD_MENUS
               continue
            if mrl and choice and ext in choice["extensions"] and \
               ext not in player["extensions"]:
                continue

        choice = player
        
    return choice["class"]


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
            # Stream ended (either stopped by user or finished)
            "end": notifier.Signal(),
            "stream_changed": notifier.Signal(),
            "frame": notifier.Signal(), # CAP_CANVAS
            "osd_configure": notifier.Signal(),  # CAP_OSD
            # Process is about to die (shared memory will go away)
            "quit": notifier.Signal()
        }

        self._state = STATE_NOT_RUNNING
        self._window = None
        self._size = None

    def __del__(self):
        print "@@@@@@@@@@@@@@@@@@ Death of", self


    def get_capabilities(self):
        return _players[self.get_player_id()]["caps"]

    def get_supported_schemes(self):
        return _players[self.get_player_id()]["schemes"]

    def has_capability(self, cap):
        supported_caps = self.get_capabilities()
        if type(cap) not in (list, tuple):
            return cap in supported_caps

        return sets.Set(cap).issubset(sets.Set(supported_caps))

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

        assert(isinstance(window, display.X11Window))
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

    def get_player_id(self):
        return None

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

    def die(self):
        """
        Kills the player.  No more files may be played once die() is called.
        """
        pass
