#!/usr/bin/python

import sys, math, threading, os, time

import kaa
from kaa import xine, display, metadata, notifier

if len(sys.argv) <= 1:
    print "Usage: %s [mrl]" % sys.argv[0]
    sys.exit(1)

mrl = sys.argv[1]
# Make argment into mrl if not already
if mrl.find("://") == -1:
    md = metadata.parse(mrl)
    if isinstance(md, (metadata.disc.dvdinfo.DVDInfo, metadata.disc.lsdvd.DVDInfo)):
        mrl = "dvd://" + mrl
    else:
        if mrl[0] != '/':
            mrl = os.path.join(os.getcwd(), mrl)
        mrl = "file://" + mrl
        print mrl

def say(line):
    if line[0] != "\n":
        sys.stdout.write(" " * 60 + "\r")
    sys.stdout.write(line + "\r")
    sys.stdout.flush()

def handle_keypress_event(key, stream, window):
    channel = stream.get_parameter(xine.PARAM_AUDIO_CHANNEL_LOGICAL)
    lang = stream.get_audio_lang(channel)

    if key == "q":
        raise SystemExit
    elif key == "f":
        window.set_fullscreen(not window.get_fullscreen())
    elif key in ("m", "menu"):
        stream.send_event(xine.EVENT_INPUT_MENU2)
    elif key == "space":
        speed = stream.get_parameter(xine.PARAM_SPEED)
        if speed == xine.SPEED_PAUSE:
            stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_NORMAL)
        else:
            stream.set_parameter(xine.PARAM_SPEED, xine.SPEED_PAUSE)
            say("\n ==== PAUSE ====\n")
    elif key == "]":
        stream.send_event(xine.EVENT_INPUT_NEXT)
    elif key == "[":
        stream.send_event(xine.EVENT_INPUT_PREVIOUS)
    elif key == "d":
        source = stream.get_video_source()
        deint_input = stream.deint_post.get_default_input()
        if source.get_wire_target() == deint_input:
            stream.deint_post.unwire()
            say("\nDeinterlacing OFF\n")
        else:
            source.wire(deint_input)
            say("\nDeinterlacing ON\n")
        

    if lang == "menu":
        d = { "up": xine.EVENT_INPUT_UP, "down": xine.EVENT_INPUT_DOWN,
              "left": xine.EVENT_INPUT_LEFT, "right": xine.EVENT_INPUT_RIGHT,
              "enter": xine.EVENT_INPUT_SELECT }
        if key in d:
            stream.send_event(d[key])
    else:
        d = { "up": 60, "down": -60, "left": -10, "right": 10 }
        if key in d:
            stream.seek_relative(d[key])

        

def handle_xine_event(event, window):
    stream = event.get_stream()
    #print "EVENT", event.type, event.data

    if event.type == xine.EVENT_UI_SET_TITLE:
        say("New title: %s\n" % event.data["str"])


def handle_aspect_changed(aspect, stream, window):
    # Resize window to video dimensions
    video_width = stream.get_info(xine.STREAM_INFO_VIDEO_WIDTH)
    height = stream.get_info(xine.STREAM_INFO_VIDEO_HEIGHT)
    width = int(math.ceil(height * window.aspect))
    if width and height and (width, height) != window.get_size():
        if window.resize((width, height)):
            say("VO: %dx%d => %dx%d\n" % (video_width, height, width, height))
        window.show()

def output_status_line(stream):
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
vo = x.open_video_driver(window = win)
ao = x.open_audio_driver()
stream = x.new_stream(ao, vo)
stream.signals["event"].connect_weak(handle_xine_event, win)

kaa.signals["stdin_key_press_event"].connect_weak(handle_keypress_event, stream, win)
win.signals["key_press_event"].connect_weak(handle_keypress_event, stream, win)
win.signals["aspect_changed"].connect_weak(handle_aspect_changed, stream, win)
kaa.signals["idle"].connect_weak(output_status_line, stream)

stream.open(mrl)
stream.play()

stream.deint_post = x.post_init("tvtime", video_targets = [vo])
methods = stream.deint_post.get_parameters_desc()["method"]["enums"]
stream.deint_post.set_parameters(method = methods.index("Greedy2Frame"))
#post.set_parameters(method = methods.index("TomsMoComp"), cheap_mode = False)

kaa.main()
win.hide()
del ao, vo, stream, x
