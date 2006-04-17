import gtk

import kaa, sys
import kaa.player, kaa.canvas, kaa.input, kaa.input.stdin

print  kaa.player.xine.config.deinterlacer.method
kaa.player.xine.config.deinterlacer.method = 'Toms'
print  kaa.player.xine.config.deinterlacer.method

if len(sys.argv) <= 1:
    print "Usage: %s [videofile]" % sys.argv[0]
    sys.exit(0)

def handle_lirc_event(code, player):
    lirc_map = { "exit": "q", "menu": "m", "select": "space",
                 "up": "up", "down": "down", "left": "left", "right": "right",
                 "display": "o", "1": "1", "2": "2", "ch-": "[", "ch+": "]"
                }

    code = code.lower()
    if code in lirc_map:
        return handle_key(lirc_map[code], player)



def handle_key(key, player):
    if key in ("space", "enter"):
        if player.is_in_menu():
            player.nav_command("select")
        else:
            player.pause_toggle()
    elif key == "q":
        player.stop()
        raise SystemExit
    elif key == "m":
        player.nav_command("menu2")
    elif key in ("up", "down", "left", "right"):
        if player.is_in_menu():
            player.nav_command(key)
        else:
            player.seek_relative({"up": 60, "down": -60, "left": -10, "right": 10}[key])
            if not osd.get_visible():
                osd_toggle()
                toggle_timer.start(3)
            elif toggle_timer.active():
                toggle_timer.start(3)

    elif key == "f" and player.get_window():
        win = player.get_window()
        win.set_fullscreen(not win.get_fullscreen())
    elif key == "o":
        osd_toggle()
    elif key == "a":
        y = sel.get_computed_pos()[1]
        sel.animate("move", top = y-20, duration = 0.1, bounce = True, decelerate = True)
    elif key == "z":
        y = sel.get_computed_pos()[1]
        sel.animate("move", top = y+20, duration = 0.1, bounce = True, decelerate = True)
    elif key == "1":
        player.delay -= 0.1
        player._slave_cmd("audio_delay -0.1")
        osd_msg("Audio delay: %0.1f" % player.delay)
    elif key == "2":
        player.delay += 0.1
        player._slave_cmd("audio_delay 0.1")
        osd_msg("Audio delay: %0.1f" % player.delay)
    elif key == "[":
        player.nav_command("prev")
    elif key == "]":
        player.nav_command("next")
        

def dump_info(player):
    player.get_window().show()
    print "Movie now playing:"
    for key, value in player.get_info().items():
        print "   %s: %s" % (key.rjust(10), str(value))

    print "Keys: space - toggle pause | q - quit | arrows - seek | f - fullscreen | o - toggle OSD"


def seconds_to_human_readable(secs):
    hrs = secs / 3600
    mins = (secs % 3600) / 60
    secs = (secs % 3600 % 60)
    if hrs >= 1:
        return "%02d:%02d:%02d" % (hrs, mins, secs)
    else:
        return "%02d:%02d" % (mins, secs)


def output_status_line(player):
    if player.get_state() != kaa.player.STATE_PLAYING:
        return

    length = player.get_info()["length"]
    pos = player.get_position()
    if length:
        percent = (pos/length)*100
    else:
        percent = 0
    pos = seconds_to_human_readable(pos)
    length = seconds_to_human_readable(length)
    line = "%s / %s (%.1f%%)" % (pos, length, percent)
    sys.stdout.write("Position: %s\r" % line)
    sys.stdout.flush()
    if osd.get_visible():
        osd_text.set_text(line)



def osd_toggle():
    if osd.get_visible():
        osd_cont.animate("move", top = "100%", duration = 0.2, end_callback = osd.hide)
        osd_cont.animate("color", a = 0, duration = 0.2)
        toggle_timer.stop()
    else:
        osd.show()
        osd_cont.animate("move", bottom = "95%", duration = 0.2, bounce=True)
        osd_cont.animate("color", a = 255, duration = 0.2)


def osd_msg(msg):
    osd_msg_text.set_text(msg)
    osd_msg_text.show()
    osd_msg_text.hide_timer.start(2)
    if not osd.get_visible():
        osd.show()
        osd.hide_timer.start(2)
    


player = kaa.player.Player()
player.open(sys.argv[1])
player.delay = 0
print "Playing file with '%s' player" % player.get_player_id()
player.signals["start"].connect(dump_info, player)
player.play()
player.get_window().set_fullscreen()
toggle_timer = kaa.notifier.OneShotTimer(osd_toggle)

osd = kaa.canvas.PlayerOSDCanvas(player)
osd.hide_timer = kaa.notifier.OneShotTimer(osd.hide)
osd_msg_text = osd.add_child(kaa.canvas.Text("", size=24), left = "5%", top = "2%")
osd_msg_text.hide_timer = kaa.notifier.OneShotTimer(osd_msg_text.hide)
osd_cont = osd.add_child(kaa.canvas.Container(), hcenter="50%", bottom = "95%")

osdbg = osd_cont.add_child(kaa.canvas.Image("data/osdbar-bg-glow.png"), 
                          width = "85%", height="12%", aspect = "ignore")
osdbg.set_border(8, 8, 8, 8)
osdgrad = osd_cont.add_child(kaa.canvas.Image("data//osdbar-bg-gradient.png"), 
                             width = "85%", height="12%", aspect = "ignore")
osdgrad.set_border(8, 8, 8, 8)
osdgrad.set_padding(5, 5, 5, 5)
osd_text = osd_cont.add_child(kaa.canvas.Text("Hello", size = 24), left = 40, vcenter="50%")
osd.show()

#osd_cont.move(0,0)
#r=osd.add_child(kaa.canvas.Rectangle(), color=(255,255,255,255), width=640, height=640)
kaa.notifier.Timer(output_status_line, player).start(0.1)

kaa.signals["stdin_key_press_event"].connect(handle_key, player)
if player.get_window():
    player.get_window().signals["key_press_event"].connect(handle_key, player)

# Enable remote control
if kaa.input.lirc.init():
    kaa.signals["lirc"].connect_weak(handle_lirc_event, player)

kaa.main()
