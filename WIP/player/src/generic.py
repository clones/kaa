import backends
import kaa.notifier
from skeleton import *

class Player(object):
    def __init__(self, window):

        global backends
        if backends:
            backends.init()
            backends = None

        self._player = None
        self._size = window.get_size()
        self._window = window
        
        # We update the signals dict if it already exists in order to play 
        # friendly with multiple inheritance.
        if not hasattr(self, "signals"):
            self.signals = {}

        self.signals.update({
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
        })


    def open(self, mrl, caps = None, player = None):
        cls = get_player_class(mrl = mrl, player = player, caps = caps)
        self._open_mrl = mrl
        self._open_caps = caps
        
        if not cls:
            raise PlayerError("No supported player found to play %s", mrl)

        if self._player != None:
            running = self._player.get_state() != STATE_NOT_RUNNING
            self._player.stop()
            if isinstance(self._player, cls):
                return self._player.open(mrl)

            # Continue open once our current player is dead.  We want to wait
            # before spawning the new one so that it releases the audio 
            # device.
            if running:
                self._player.signals["quit"].connect_once(self._open, mrl, cls)
                self._player.die()
                return

        return self._open(mrl, cls)


    def _open(self, mrl, cls):
        # TODO: Don't create new player instance if player class is the same
        # as the current player.
        self._player = cls()

        for signal in self.signals:
            if signal in self._player.signals and \
                   not signal in ('start', 'failed', 'open'):
                self._player.signals[signal].connect_weak(self.signals[signal].emit)

        self._player.open(mrl)
        self._player.set_window(self._window)
        self._player.set_size(self._size)
        self.signals['open'].emit()
        

    @kaa.notifier.yield_execution()
    def play(self, __player_list=None, **kwargs):
        if not self._player:
            raise PlayerError, "Play called before open"
            yield False

        if self._open in self._player.signals["quit"]:
            block = kaa.notifier.InProgress()
            self.signals['open'].connect_once(block.finished, True)
            yield block
            
        state = self._player.get_state()
        self._player.play(**kwargs)
        if state == self._player.get_state() or \
               self._player.get_state() != STATE_OPENING:
            yield True
            
        block = kaa.notifier.InProgress()
        self._player.signals['failed'].connect_once(block.finished, False)
        self._player.signals['start'].connect_once(block.finished, True)
        yield block
        self._player.signals['failed'].disconnect(block.finished)
        self._player.signals['start'].disconnect(block.finished)
        if not block():
            if __player_list is None:
                __player_list = get_all_player()
            if self._player._player_id in __player_list:
                __player_list.remove(self._player._player_id)
            if not __player_list:
                self.signals['failed'].emit()
                yield False
            print 'unable to play with %s, try %s' % \
                  (self._player._player_id, __player_list[0])
            self.open(self._open_mrl, self._open_caps, player=__player_list[0])
            sync = self.play(__player_list, **kwargs)
            # wait for the recursive call to return and return the
            # given value (True or False)
            yield sync
            yield sync()
        self.signals['start'].emit()
        yield True

        
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
            return self._player.get_position()
        return 0.0

    def get_info(self):
        if self._player:
            return self._player.get_info()
        return {}

    def nav_command(self, input):
        if self._player:
            self._player.nav_command(input)

    def is_in_menu(self):
        if self._player:
            return self._player.is_in_menu()
        return False

    def get_player_id(self):
        if self._player:
            return self._player._player_id
        return ''
    
    def get_window(self):
        if self._player:
            return self._player.get_window()

    def has_capability(self, cap):
        if self._player:
            return self._player.has_capability(cap)

    def osd_can_update(self):
        if self._player:
            return self._player.osd_can_update()

    def osd_update(self, *args, **kwargs):
        if self._player:
            return self._player.osd_update(*args, **kwargs)
        
    def unlock_frame_buffer(self):
        if self._player:
            return self._player.unlock_frame_buffer()

    def get_state(self):
        if self._player:
            return self._player.get_state()

    def die(self):
        if self._player:
            return self._player.die()

    def set_size(self, size):
        self._size = size
        if self._player:
            return self._player.set_size(size)
