import sys

import kaa
import kaa.display
import kaa.player

window = kaa.display.X11Window(size = (800,600), title = "kaa.player")

player = kaa.player.Player(window)
player.signals["start"].connect_once(window.show)
player.open(sys.argv[1], player='gstreamer')
player.play()

kaa.main()
