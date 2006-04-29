#!/usr/bin/python

import sys, math, threading, os, time, gc

import kaa, kaa.input, kaa.input.stdin
from kaa import xine, display, metadata, notifier


#
# some debug code
#

def say(line):
    if line[0] != "\n":
        sys.stdout.write(" " * 60 + "\r")
    sys.stdout.write(line + "\r")
    sys.stdout.flush()


def seconds_to_human_readable(secs):
    hrs = secs / 3600
    mins = (secs % 3600) / 60
    secs = (secs % 3600 % 60)
    if hrs:
        return "%02d:%02d:%02d" % (hrs, mins, secs)
    else:
        return "%02d:%02d" % (mins, secs)


def output_status_line(stream):
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




#
# event handling
#


def handle_xine_event(event):
    stream = event.get_stream()
    #print "EVENT", stream, event.type, event.data

    if event.type == xine.EVENT_UI_SET_TITLE:
        say("New title: %s\n" % event.data["str"])
    elif event.type == xine.EVENT_UI_NUM_BUTTONS:
        stream.is_in_menu = event.data["num_buttons"] > 0
    elif event.type == xine.EVENT_UI_PLAYBACK_FINISHED:
        stream.stop()
        sys.exit(0)


def handle_keypress_event(key, stream):
    title = stream.get_info(xine.STREAM_INFO_DVD_TITLE_NUMBER)
    if key == "q":
        stream.stop()
        raise SystemExit



#
# test code
#

if len(sys.argv) <= 1:
    print "Usage: %s [mrl]" % sys.argv[0]
    sys.exit(1)

# create xine object
x = xine.Xine()

# configure me! x11, fb or dfb
DISPLAY_TYPE = 'x11'


# create display and vo
if DISPLAY_TYPE == 'x11':
    win = display.X11Window(size = (50, 50), title = "Kaa Player")
    win.set_cursor_hide_timeout(0.5)
    win._aspect = -1

    vo = x.open_video_driver(
        "xv", wid = win.get_id(),
        frame_output_cb = notifier.WeakCallback(x._default_frame_output_cb, win), 
        dest_size_cb = notifier.WeakCallback(x._default_dest_size_cb, win))

    # Hook the first resize event so we can show the window once we're resized
    # to the proper movie size.
    def handle_resize(old, new, window):
        window.show()
        vo.send_gui_data(xine.GUI_SEND_VIDEOWIN_VISIBLE, 1)

    def configure_event(pos, size, window):
        vo.send_gui_data(xine.GUI_SEND_DRAWABLE_CHANGED, window.get_id())

    win.signals["resize_event"].connect_once(handle_resize, win)
    win.signals["configure_event"].connect_weak(configure_event, win)

elif DISPLAY_TYPE == 'fb':
    win = display.Framebuffer()
    vo = x.open_video_driver("vidixfb")

# create auido
ao = x.open_audio_driver()

# create stream
stream = x.new_stream(ao, vo)
stream.signals["event"].connect(handle_xine_event)

kaa.signals["step"].connect_weak(output_status_line, stream)
kaa.signals["stdin_key_press_event"].connect_weak(handle_keypress_event, stream)

stream.open(sys.argv[1])
stream.play()

kaa.main()
if DISPLAY_TYPE == 'x11':
    win.hide()
