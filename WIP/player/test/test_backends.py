import sys

import kaa
import kaa.display
import kaa.player

def print_msg(msg):
    print '>', msg

def next(id):
    print 'play with', id
    player.open(sys.argv[1], player=id)
    player.play()
    
window = kaa.display.X11Window(size = (800,600), title = "kaa.player")

player = kaa.player.Player(window)
player.signals["start"].connect_once(window.show)
player.signals["start"].connect(print_msg, 'playback started')
player.signals["end"].connect(print_msg, 'playback end')
player.signals["failed"].connect(print_msg, 'playback failed')


kaa.notifier.OneShotTimer(next, 'xine').start(0)
kaa.notifier.OneShotTimer(next, 'gstreamer').start(5)
kaa.notifier.OneShotTimer(next, 'mplayer').start(10)
kaa.notifier.OneShotTimer(next, 'xine').start(15)
kaa.notifier.OneShotTimer(next, 'gstreamer').start(20)
kaa.notifier.OneShotTimer(next, 'mplayer').start(25)

kaa.main()
