import pygst
pygst.require('0.10')
import gst
import sys
import time

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
#
# The bad news:
#
# o The doc sucks. What properties are there?
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

player = gst.element_factory_make("playbin", "player")
# change the videosink to be in kaa.display

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
