import sys
import logging

import kaa
import kaa.display
import kaa.popcorn
import kaa.input.stdin

logging.getLogger('popcorn').setLevel(logging.INFO)
# logging.getLogger('popcorn.child').setLevel(logging.ERROR)


def print_msg(msg):
    print '>', msg

def next(id):
    print 'play with', id
    player.open(sys.argv[1], player=id)
    player.play()

def handle_key(key, player):
    if key in ("space", "enter"):
        player.pause_toggle()
    elif key == "q":
        player.stop()
    elif key in ("up", "down", "left", "right"):
        player.seek({"up": 60, "down": -60, "left": -10, "right": 10}[key])
    elif key == "f" and player.get_window():
        win = player.get_window()
        win.set_fullscreen(not win.get_fullscreen())

window = kaa.display.X11Window(size = (800,600), title = "kaa.popcorn")

player = kaa.popcorn.Player(window)
player.signals["start"].connect_once(window.show)
player.signals["start"].connect(print_msg, 'playback started')
player.signals["end"].connect(print_msg, 'playback end')
# player.signals["end"].connect(next, 'xine')
player.signals["failed"].connect(print_msg, 'playback failed')

kaa.signals["stdin_key_press_event"].connect(handle_key, player)
if player.get_window():
    player.get_window().signals["key_press_event"].connect(handle_key, player)

kaa.notifier.OneShotTimer(next, 'xine').start(0)
kaa.notifier.OneShotTimer(player.stop).start(1)

def print_pos():
    print '\r', player.get_position(),
    sys.stdout.flush()
    return True

kaa.notifier.Timer(print_pos).start(0.1)
kaa.main()
