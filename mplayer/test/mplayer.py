#!/usr/bin/python

import kaa
import kaa.mplayer
from kaa.mplayer import MPlayer
from kaa import display, main, notifier
import sys

#kaa.mplayer.DEBUG=3

def handle_key(key, mp):
    if key == "space":
        mp.pause()
    elif key == "q":
        sys.exit(0)
    elif key in ("up", "down", "left", "right"):
        mp.seek({"up": 60, "down": -60, "left": -10, "right": 10}[key])
    elif key == "f":
        win = mp.get_window()
        win.set_fullscreen(not win.get_fullscreen())
    elif key == "s":
        mp.get_window().show()

def dump_info(mp):
    print "Movie now playing:"
    for key, value in mp.get_file_info().items():
        print "   %s: %s" % (key.rjust(10), str(value))

    print "Keys: space - toggle pause | q - quit | arrows - seek | f - fullscreen"

def output_status_line(pos, mp):
    length = mp.get_file_info()["length"]
    if length:
        percent = (pos/length)*100
    else:
        percent = 0
    sys.stdout.write("Position: %.1f / %.1f (%.1f%%)\r" % (pos, length, percent))
    sys.stdout.flush()


mp = MPlayer((800, 600))
mp.play(sys.argv[1])
mp.get_window().signals["key_press_event"].connect(handle_key, mp)
#mp.get_window().signals["map_event"].connect_weak_once(lambda win: win.hide(), mp.get_window())
kaa.signals["stdin_key_press_event"].connect(handle_key, mp)
mp.signals["start"].connect(dump_info, mp)
mp.signals["tick"].connect(output_status_line, mp)
mp.signals["quit"].connect(kaa.shutdown)

main()
print "Shut down"
