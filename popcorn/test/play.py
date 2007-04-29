import sys
import logging

import kaa
import kaa.display
import kaa.popcorn
import kaa.input.stdin

logging.getLogger('popcorn').setLevel(logging.INFO)
logging.getLogger('popcorn.child').setLevel(logging.DEBUG)

BACKEND = 'xine'                        # mplayer, xine, gstreamer
WINDOW  = '16:9'                         # '4:3', '16:3', 'none'

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


kaa.popcorn.config.load('popcorn.conf')
kaa.popcorn.config.save('popcorn.conf')

if WINDOW == 'none':
    player = kaa.popcorn.Player()
else:
    if WINDOW == '16:9':
        window = kaa.display.X11Window(size = (800,450), title = "kaa.popcorn")
    else:
        window = kaa.display.X11Window(size = (800,600), title = "kaa.popcorn")
    player = kaa.popcorn.Player(window)
    player.signals["start"].connect_once(window.show)
    
player.signals["start"].connect(print_msg, 'playback started')
player.signals["end"].connect(print_msg, 'playback end')
# player.signals["end"].connect(next, BACKEND)
player.signals["failed"].connect(print_msg, 'playback failed')

kaa.signals["stdin_key_press_event"].connect(handle_key, player)
if player.get_window():
    player.get_window().signals["key_press_event"].connect(handle_key, player)

kaa.notifier.OneShotTimer(next, BACKEND).start(0)
#kaa.notifier.OneShotTimer(player.stop).start(1)

def print_pos():
    print '\r', player.get_position(),
    sys.stdout.flush()
    return True

def do_something1():
    player.set_property('scale', kaa.popcorn.SCALE_IGNORE)
    
def do_something2():
    player.set_property('scale', kaa.popcorn.SCALE_KEEP)

def do_zoom():
    player.set_property('zoom', player.get_property('zoom') - 10)

kaa.notifier.Timer(print_pos).start(0.1)
# kaa.notifier.OneShotTimer(do_something1).start(2)
# kaa.notifier.OneShotTimer(do_something2).start(4)
# kaa.notifier.Timer(do_zoom).start(2)
kaa.main()
