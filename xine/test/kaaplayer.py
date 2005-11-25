#!/usr/bin/python

import sys, math, threading, os, time, gc

import kaa, kaa.input
from kaa import xine, display, metadata, notifier

if len(sys.argv) <= 1:
    print "Usage: %s [mrl]" % sys.argv[0]
    sys.exit(1)

play_files = sys.argv[1:]

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
    title = stream.get_info(xine.STREAM_INFO_DVD_TITLE_NUMBER)
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
        enabled = deint_post.get_parameters()["enabled"]
        deint_post.set_parameters(enabled = not enabled)
        if enabled:
            say("\nDeinterlacing OFF\n")
        else:
            say("\nDeinterlacing ON\n")
    elif key == "t":
        pulldown = 1 - deint_post.get_parameters()["pulldown"]
        deint_post.set_parameters(pulldown = pulldown)
        if pulldown:
            say("\nPulldown OFF\n")
        else:
            say("\nPulldown ON\n")

    if stream.is_in_menu:
        d = { "up": xine.EVENT_INPUT_UP, "down": xine.EVENT_INPUT_DOWN,
              "left": xine.EVENT_INPUT_LEFT, "right": xine.EVENT_INPUT_RIGHT,
              "enter": xine.EVENT_INPUT_SELECT, "space": xine.EVENT_INPUT_SELECT }
        if key in d:
            stream.send_event(d[key])
    else:
        d = { "up": 60, "down": -60, "left": -10, "right": 10 }
        if key in d:
            stream.seek_relative(d[key])
        if key == "space":
            key = "p"

    if key == "p":
        speed = stream.get_parameter(xine.PARAM_SPEED)
        if speed == xine.SPEED_PAUSE:
            stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
        else:
            stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)
            say("\n ==== PAUSE ====\n")

    if key == "n":
        play_next_queued()


def play_next_queued():
    global goom_post, play_files, stream

    if len(play_files) == 0:
        sys.exit(0)

    stream.stop()
    file = play_files.pop(0)
    # Make argment into mrl if not already
    mrl = xine.make_mrl(file)
    stream.open(mrl)

    if not stream.get_info(xine.STREAM_INFO_HAS_VIDEO):
        if not goom_post:
            goom_post = x.post_init("goom", video_targets = [vo], audio_targets=[ao])
            if "volnorm" in x.list_post_plugins():
                volnorm_post = x.post_init("volnorm", audio_targets=[ao])
                goom_post.get_output("audio out").wire(volnorm_post.get_default_input())
        stream.get_audio_source().wire(goom_post.get_default_input())
    else:
        stream.get_audio_source().wire(ao)
        goom_post = None

    stream.play()
    xine._debug_show_chain(stream._obj)
    gc.collect()


def handle_xine_event(event):
    stream = event.get_stream()
    #print "EVENT", stream, event.type, event.data

    if event.type == xine.EVENT_UI_SET_TITLE:
        say("New title: %s\n" % event.data["str"])
    elif event.type == xine.EVENT_UI_NUM_BUTTONS:
        stream.is_in_menu = event.data["num_buttons"] > 0
    elif event.type == xine.EVENT_UI_PLAYBACK_FINISHED:
        play_next_queued()


def seconds_to_human_readable(secs):
    hrs = secs / 3600
    mins = (secs % 3600) / 60
    secs = (secs % 3600 % 60)
    if hrs:
        return "%02d:%02d:%02d" % (hrs, mins, secs)
    else:
        return "%02d:%02d" % (mins, secs)


def output_status_line(stream, window):
    if stream.get_parameter(xine.PARAM_SPEED) == xine.SPEED_PAUSE:
        return
    pos, time, length = stream.get_pos_length()
    if length:
        percent = (time/length)*100
    else:
        percent = 0
    time = seconds_to_human_readable(time)
    length = seconds_to_human_readable(length)
    say("Position: %s / %s (%.1f%%)" % (time, length, percent))


win = display.X11Window(size = (50, 50), title = "Kaa Player")
win.set_cursor_hide_timeout(0.5)

x = xine.Xine()
# Test various vo drivers.
#vo = x.open_video_driver("kaa", passthrough = "xv", window=win)
#vo = x.open_video_driver("xshm", window = win)
#vo = x.open_video_driver("sdl", window = win)
vo = x.open_video_driver("xv", window = win)

ao = x.open_audio_driver()
stream = x.new_stream(ao, vo)
stream.is_in_menu = False
stream.signals["event"].connect(handle_xine_event)

kaa.signals["idle"].connect_weak(output_status_line, stream, win)
kaa.signals["stdin_key_press_event"].connect_weak(handle_keypress_event, stream, win)
win.signals["key_press_event"].connect_weak(handle_keypress_event, stream, win)

# Enable remote control
if kaa.input.lirc.init():
    kaa.signals["lirc"].connect_weak(handle_lirc_event, stream, win)

def handle_resize(old, new, window):
    window.show()
    window.set_fullscreen()

# Hook the first resize event so we can show the window once we're resized
# to the proper movie size.
win.signals["resize_event"].connect_once(handle_resize, win)

deint_post = x.post_init("tvtime", video_targets = [vo])
deint_post.set_parameters(method = "GreedyH", enabled = True)
#print deint_post.get_parameters_desc()
#print deint_post.get_parameters()
stream.get_video_source().wire(deint_post.get_default_input())
#deint_post.set_parameters(cheap_mode = True)
#deint_post.set_parameters(framerate_mode = "half_top")

#expand = x.post_init("expand", video_targets = [vo])
#stream.get_video_source().wire(expand.get_default_input())

#x.set_config_value("effects.goom.fps", 20)
x.set_config_value("effects.goom.width", 512)
x.set_config_value("effects.goom.height", 384)
x.set_config_value("effects.goom.csc_method", "Slow but looks better")

goom_post = None

play_next_queued()

kaa.main()
win.hide()

# Test garbage collection
del stream, ao, vo, x, win, goom_post, deint_post
gc.collect()
