#!/usr/bin/python

import sys, math, threading, os, time, gc

import kaa, kaa.input, kaa.input.stdin
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
                 "ch-": "[", "ch+": "]", "input": "p",
                 "up": "up", "down": "down", "left": "left", "right": "right",
                 "skip": "n", "pause": "pause", "ffwd": ">", "rew": "<",
                 "play": "play"
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
    elif key == "D":
        method = deint_post.get_parameters()["method"]
        methods = ["Linear", "GreedyH", "TomsMoComp", "Linear"]
        deint_post.set_parameters(method = methods[methods.index(method)+1])
        #deint_post.set_parameters(method = {"GreedyH": "TomsMoComp", "TomsMoComp": "GreedyH"}[method])
        say("\nDeinterlacing method: %s\n" % deint_post.get_parameters()["method"])
    elif key == "c":
        cheap = deint_post.get_parameters()["cheap_mode"]
        deint_post.set_parameters(cheap_mode = not cheap)
        if cheap:
            say("\nCheap mode OFF\n")
        else:
            say("\nCheap mode ON\n")
    elif key == "C":
        frame = deint_post.get_parameters()["framerate_mode"]
        deint_post.set_parameters(framerate_mode = {"full": "half_bottom", "half_bottom": "full"}[frame])
        if frame == "full":
            say("\nHALF framerate mode\n")
        else:
            say("\nFULL framerate mode\n")

    elif key == "t":
        pulldown = deint_post.get_parameters()["pulldown"]
        deint_post.set_parameters(pulldown = {"none": "vektor", "vektor":"none"}[pulldown])
        if pulldown == "none":
            say("\nPulldown ON\n")
        else:
            say("\nPulldown OFF\n")

    if key == "pause":
        stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)
    elif key == "play":
        stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
    elif key == ">":
        stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_FAST_4)
    elif key == "<":
        stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_SLOW_4)
        
    if key == "n":
        play_next_queued()

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

    if key == "N":
        strength = noise.get_parameters()["luma_strength"]
        if strength > 0:
            noise.set_parameters(luma_strength = 0, chroma_strength = 0)
            print "NOISE off"
        else:
            noise.set_parameters(luma_strength = 8, chroma_strength = 5)
            print "NOISE on"


def play_next_queued():
    global goom_post, play_files, stream

    if len(play_files) == 0:
        sys.exit(0)

    stream.stop()
    file = play_files.pop(0)
    mrl = file
    stream.open(mrl)

    if not stream.get_info(xine.STREAM_INFO_HAS_VIDEO):
        if not goom_post:
            goom_post = x.post_init("goom", video_targets = [vo], audio_targets=[ao])
            #if "volnorm" in x.list_post_plugins():
            #    volnorm_post = x.post_init("volnorm", audio_targets=[ao])
            #    goom_post.get_output("audio out").wire(volnorm_post.get_default_input())
        stream.get_audio_source().wire(goom_post.get_default_input())
    else:
        stream.get_audio_source().wire(ao)
        goom_post = None

    stream.play()
    xine._debug_show_chain(stream._obj)
    gc.collect()
    print "Now playing:", file


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
#vo = x.open_video_driver("xv", window = win)
win._aspect = -1
vo = x.open_video_driver("xv", wid = win.get_id(), frame_output_cb = notifier.WeakCallback(x._default_frame_output_cb, win), 
    dest_size_cb = notifier.WeakCallback(x._default_dest_size_cb, win))

ao = x.open_audio_driver()
stream = x.new_stream(ao, vo)
stream.signals["event"].connect(handle_xine_event)
stream.is_in_menu = False

kaa.signals["step"].connect_weak(output_status_line, stream, win)
kaa.signals["stdin_key_press_event"].connect_weak(handle_keypress_event, stream, win)
win.signals["key_press_event"].connect_weak(handle_keypress_event, stream, win)

# Enable remote control
if kaa.input.lirc.init():
    kaa.signals["lirc"].connect_weak(handle_lirc_event, stream, win)

def handle_resize(old, new, window):
    window.show()
    vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, 1)
    window.set_fullscreen()

def configure_event(pos, size, window):
    vo.send_gui_data(xine.GUI_SEND_DRAWABLE_CHANGED, window.get_id())


# Hook the first resize event so we can show the window once we're resized
# to the proper movie size.
win.signals["resize_event"].connect_once(handle_resize, win)
win.signals["configure_event"].connect_weak(configure_event, win)


deint_post = x.post_init("tvtime", video_targets = [vo])
deint_post.set_parameters(method = "GreedyH", enabled = True, chroma_filter = True)
#deint_post.set_parameters(method = "TomsMoComp", enabled = True, chroma_filter = True)
stream.get_video_source().wire(deint_post.get_default_input())
#deint_post.set_parameters(cheap_mode = True)
#deint_post.set_parameters(framerate_mode = "half_top")

expand = x.post_init("expand", video_targets = [vo])
#stream.get_video_source().wire(expand.get_default_input())

#noise = x.post_init("noise", video_targets = [vo])
#deint_post.get_default_output().wire(noise.get_default_input())
#stream.get_video_source().wire(noise.get_default_input())

x.set_config_value("effects.goom.fps", 20)
x.set_config_value("effects.goom.width", 512)
x.set_config_value("effects.goom.height", 384)
x.set_config_value("effects.goom.csc_method", "Slow but looks better")

eq2_post = x.post_init("eq2", video_targets = [vo])
eq2_post.set_parameters(gamma = 1.2, contrast = 1.1)
#noise.get_default_output().wire(eq2_post.get_default_input())
#stream.get_video_source().wire(eq2_post.get_default_input())


#stream.get_video_source().wire(vo)
goom_post = None

play_next_queued()

kaa.main()
win.hide()

# Test garbage collection
del stream, ao, vo, x, win, goom_post, deint_post, expand, eq2_post
gc.collect()
