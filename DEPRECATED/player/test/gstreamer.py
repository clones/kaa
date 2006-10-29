import pygst
pygst.require('0.10')
import gst
import sys
import time

import kaa.display

#
# play an uri like file:///home/foo/bar.mp3
# works for audio and video files
#
# The good new for kaa.player:
#
# o Simple interface. In most cases you don't call the real function, you
#   call set_property, get_gproperty and stuff like that. With gst in an extra
#   process this makes it easy to control over kaa.rpc
# o we don't need the gst mainloop (we could if we want using the gtk main loop
#   of pynotifier but this requires gtk, gobject is not powerful enough.
# o it shouldn't be a big problem to add kaa.display and kaa.canvas support to it
#
# The good news for kaa.record
#
# o We can use the gst pipe code to decode and change the stuff we want
#   (see multifdsink and all the fd/rtp/udp filter)
#
# The bad news:
#
# o The doc sucks. What properties are there?
#   Answer: looks like gst-inspect can help, e.g. to get more information
#   about xv output call 'gst-inspect-0.10 xvimagesink'
#
# o The examples for gst-python 0.10.x are all based on 0.8 and do not work.
#
#
# Doc:
#
# http://gstreamer.freedesktop.org/data/doc/gstreamer/stable/manual/html/index.html
# (understand gst and try to guess the python calls)
# http://gstreamer.freedesktop.org/documentation/ (some links broken)
# http://pygstdocs.berlios.de (not helping much)
# http://www.fluendo.com/elisa/ (read the source)
#

# Create kaa.display window. It looks like gstreamer only has support
# for X and XV output right now. That sucks, no mga and no dfb.
window = kaa.display.X11Window(size = (400,600), title = "kaa.player")
window.show()

vo = gst.element_factory_make("xvimagesink", "vo")
vo.set_xwindow_id(long(window.get_id()))
vo.set_property('force-aspect-ratio', True)

# now create the player and set the output
player = gst.element_factory_make("playbin", "player")
player.set_property('video-sink', vo)

# TODO: how to add some extra filter to the chain? An kaa.canvas overlay filter
# needs to be written (take a look at the pango stuff that is used to write
# subtitles: textoverlay) and connected. To support videos aspect != window aspect
# some sort of expand filter is also needed (videobox or videoscale).

# I tried to add a filter similar to the one we need for kaa.canvas. The
# dicetv effect looks like a nice way to test it. But playbin does not support
# adding more filter into the video chain (which is type gst.Bin). Other
# code examples like totel or Elisa use some trick to create a new Bin, use that
# as video-sink for playbin and add effect + real output in that bin. But I failed
# to setup and connect the bin.

# Idea
#
# | vo_sink = gst.Bin()
# | effect = gst.element_factory_make("dicetv", "effect")
# | vo_sink.add(effect)
# | vo_sink.add(vo)
# | effect.link(vo)
#
# The linking fails when vo has the window id set. No idea why this
# happens. Ignore that and continue
#
# | pad = effect.get_pad('sink')
# | ghostpad = gst.GhostPad("sink", pad)
# | vo_sink.add_pad(ghostpad)
#
# No idea why the sink pad from effect is the sink pad for vo_sink. But totem
# does this this way (search for puzzle in the code). So this looks correct
# but does not work because of set_xwindow_id. Doing that after the linking
# will freeze gstreamer. So I give up for now. We also need a way to add new
# effects to add a simple deinterlace.
# 
#
# for audio files, add goom this works. But using the vis-plugin code to
# inject the effect object does not work. So code for playbin in plugins base
# has some ascii art how things are plugged together.
#
# | goom = gst.element_factory_make("goom", "goom")
# | player.set_property('vis-plugin', goom)

print 'Playing:', sys.argv[1]
player.set_property('uri', sys.argv[1])

player.set_state(gst.STATE_PLAYING)

# play 10 sec
i = 100
print
while i:
    i -= 1
    pos = float(player.query_position(gst.FORMAT_TIME)[0] / 1000000) / 1000
    print '\r', pos,
    sys.stdout.flush()
    # we can sleep, gst is a thread. The gobject main loop is needed to
    # get messages from the player. Since we need to poll anyway to get the
    # current position, we can also get state change information. So no
    # special main loop is needed
    time.sleep(0.1)

# seek to 30 sec
player.seek(1.0, gst.FORMAT_TIME,
            gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
            gst.SEEK_TYPE_SET, 30000000000,
            gst.SEEK_TYPE_NONE, 0)

# play 10 sec
i = 100
while i:
    i -= 1
    pos = float(player.query_position(gst.FORMAT_TIME)[0] / 1000000) / 1000
    print '\r', pos,
    sys.stdout.flush()
    time.sleep(0.1)
print
print 'stop'
