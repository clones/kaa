import sys

import kaa
import kaa.display
import kaa.player

window = kaa.display.X11Window(size = (800,600), title = "kaa.player")
window.show()

player = kaa.player.Player(window)
player.open(sys.argv[1], player='xine')
player.play()

kaa.main()
