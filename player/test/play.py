import kaa, sys
import kaa.player

if len(sys.argv) <= 1:
    print "Usage: %s [videofile]" % sys.argv[0]
    sys.exit(0)

cls = kaa.player.get_player_class(sys.argv[1])
if not cls:
    print "No supported player found to play:", sys.argv[1]
    sys.exit(0)

def handle_key(key, player):
    if key == "space":
        player.pause_toggle()
    elif key == "q":
        raise SystemExit
    elif key in ("up", "down", "left", "right"):
        player.seek_relative({"up": 60, "down": -60, "left": -10, "right": 10}[key])
    elif key == "f" and player.get_window():
        win = player.get_window()
        win.set_fullscreen(not win.get_fullscreen())

def dump_info(player):
    player.get_window().show()
    print "Movie now playing:"
    for key, value in player.get_info().items():
        print "   %s: %s" % (key.rjust(10), str(value))

    print "Keys: space - toggle pause | q - quit | arrows - seek | f - fullscreen"

def output_status_line(player):
    if player.get_state() != kaa.player.STATE_PLAYING:
        return

    length = player.get_info()["length"]
    pos = player.get_position()
    if length:
        percent = (pos/length)*100
    else:
        percent = 0
    sys.stdout.write("Position: %.1f / %.1f (%.1f%%)\r" % (pos, length, percent))
    sys.stdout.flush()


player = cls()
print "Playing file with '%s' player" % player.get_player_id()
player.open(sys.argv[1])
player.signals["start"].connect(dump_info, player)
player.play()

kaa.notifier.Timer(output_status_line, player).start(0.1)
kaa.signals["stdin_key_press_event"].connect(handle_key, player)
if player.get_window():
    player.get_window().signals["key_press_event"].connect(handle_key, player)

kaa.main()
