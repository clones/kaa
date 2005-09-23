#!/usr/bin/python

import sys, math, threading, os, time, gc

import kaa, kaa.input
from kaa import xine, display, metadata, notifier

if len(sys.argv) <= 1:
    print "Usage: %s [mrl]" % sys.argv[0]
    sys.exit(1)

# Make argment into mrl if not already
mrl = xine.make_mrl(sys.argv[1])

def say(line):
    if line[0] != "\n":
        sys.stdout.write(" " * 60 + "\r")
    sys.stdout.write(line + "\r")
    sys.stdout.flush()

def handle_lirc_event(code, stream, window):
    lirc_map = { "exit": "q", "menu": "m", "select": "space",
                 "ch-": "[", "ch+": "]", "input": "d",
                 "up": "up", "down": "down", "left": "left", "right": "right"
                }

    code = code.lower()
    if code in lirc_map:
        return handle_keypress_event(lirc_map[code], stream, window)


def handle_keypress_event(key, stream, window):
    channel = stream.get_parameter(xine.PARAM_AUDIO_CHANNEL_LOGICAL)
    lang = stream.get_audio_lang(channel)

    if key == "q":
        stream.stop()
        raise SystemExit
    elif key == "f":
        window.set_fullscreen(not window.get_fullscreen())
    elif key in ("m", "menu"):
        stream.send_event(xine.EVENT_INPUT_MENU2)
    elif key == "]":
        stream.send_event(xine.EVENT_INPUT_NEXT)
    elif key == "[":
        stream.send_event(xine.EVENT_INPUT_PREVIOUS)
    elif key == "d":
        enabled = stream.deint_post.get_parameters()["enabled"]
        stream.deint_post.set_parameters(enabled = not enabled)
        if enabled:
            say("\nDeinterlacing OFF\n")
        else:
            say("\nDeinterlacing ON\n")

    if lang == "menu":
        d = { "up": xine.EVENT_INPUT_UP, "down": xine.EVENT_INPUT_DOWN,
              "left": xine.EVENT_INPUT_LEFT, "right": xine.EVENT_INPUT_RIGHT,
              "enter": xine.EVENT_INPUT_SELECT, "space": xine.EVENT_INPUT_SELECT }
        if key in d:
            stream.send_event(d[key])
    else:
        d = { "up": 60, "down": -60, "left": -10, "right": 10 }
        if key in d:
            stream.seek_relative(d[key])
        elif key == "space":
            speed = stream.get_parameter(xine.PARAM_SPEED)
            if speed == xine.SPEED_PAUSE:
                stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
            else:
                stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)
                say("\n ==== PAUSE ====\n")
        

def handle_xine_event(event, window):
    stream = event.get_stream()
    #print "EVENT", event.type, event.data

    if event.type == xine.EVENT_UI_SET_TITLE:
        say("New title: %s\n" % event.data["str"])


def output_status_line(stream, window):
    if stream.get_parameter(xine.PARAM_SPEED) == xine.SPEED_PAUSE:
        return
    pos, time, length = stream.get_pos_length()
    if length:
        percent = (time/length)*100
    else:
        percent = 0
    say("Position: %.1f / %.1f (%.1f%%)" % (time, length, percent))


win = display.X11Window(size = (50, 50), title = "Kaa Player")
win.set_cursor_hide_timeout(0.5)

x = xine.Xine()
#vo = x.open_video_driver("xshm", window = win)
vo = x.open_video_driver("xv", window = win)

ao = x.open_audio_driver()
stream = x.new_stream(ao, vo)

kaa.signals["idle"].connect_weak(output_status_line, stream, win)
kaa.signals["stdin_key_press_event"].connect_weak(handle_keypress_event, stream, win)
win.signals["key_press_event"].connect_weak(handle_keypress_event, stream, win)

# Enable remote control
if kaa.input.lirc.init():
    kaa.signals["lirc"].connect_weak(handle_lirc_event, stream, win)

def handle_resize(old, new, window):
    window.show()
    #window.set_fullscreen()

# Hook the first resize event so we can show the window once we're resized
# to the proper movie size.
win.signals["resize_event"].connect_once(handle_resize, win)

stream.deint_post = x.post_init("tvtime", video_targets = [vo])
stream.deint_post.set_parameters(method = "GreedyH", enabled = True)
stream.get_video_source().wire(stream.deint_post.get_default_input())
#stream.deint_post.set_parameters(cheap_mode = True)
#stream.deint_post.set_parameters(framerate_mode = "half_top")

xine._debug_show_chain(stream._obj)

stream.open(mrl)
stream.play()

kaa.main()
win.hide()

# Test garbage collection
del stream, ao, vo, x, win
gc.collect()
