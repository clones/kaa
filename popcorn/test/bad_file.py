import sys

import kaa
import kaa.display
import kaa.player

def print_msg(msg):
    print '>', msg

window = kaa.display.X11Window(size = (800,600), title = "kaa.player")

player = kaa.player.Player(window)
player.signals["start"].connect_once(window.show)
player.signals["start"].connect(print_msg, 'playback started')
player.signals["end"].connect(print_msg, 'playback end')
player.signals["failed"].connect(print_msg, 'playback failed')

player.open('/')
player.play()

kaa.main()
