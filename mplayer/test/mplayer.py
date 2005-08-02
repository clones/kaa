#!/usr/bin/python

import kaa
import kaa.mplayer
from kaa.mplayer import MPlayer
from kaa import display, main
import sys

#kaa.mplayer.DEBUG=3

def handle_key(key, mp):
    if key == "space":
        mp.pause()
    elif key == "q":
        mp.quit()
    elif key in ("up", "down", "left", "right"):
        mp.seek({"up": 60, "down": -60, "left": -10, "right": 10}[key])
    elif key == "f":
        win = mp.get_window()
        win.set_fullscreen(not win.get_fullscreen())

def dump_info(mp):
    print "Movie now playing:"
    for key, value in mp.info.items():
        print "   %s: %s" % (key.rjust(10), str(value))

    print "Keys: space - toggle pause | q - quit | arrows - seek | f - fullscreen"

mp = MPlayer((640, 480))
mp.play(sys.argv[1])
mp.get_window().signals["key_press_event"].connect(handle_key, mp)
kaa.signals["stdin_key_press_event"].connect(handle_key, mp)
mp.signals["start"].connect(dump_info, mp)
mp.signals["quit"].connect(lambda: kaa.shutdown())
main()
