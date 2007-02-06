#!/usr/bin/python
import pygst
pygst.require('0.10')
import gst
import gobject
import sys
import time
import os

import kaa.record2

filtername2obj = {}

def onNewPad(splitter, pad):
    global filtername2obj
    print "\n---"
    print "pad added!"
    print 'PAD:',pad
    print 'PADNAME:',pad.get_name()
    print 'PADCAPS:',pad.get_caps()
    if not filtername2obj.has_key(pad.get_name()):
        print "NOT FOUND"
        return
#    print pad.get_caps()[0]
#    print pad.get_caps()[0].get_name()
#    format = pad.get_caps()[0].get_name()
    print "OBJNAME:", filtername2obj[pad.get_name()].get_name()
    pad.link(filtername2obj[pad.get_name()].get_compatible_pad(pad))

    print "---"


def main():
    global foo
    
    fdsrc = gst.element_factory_make("filesrc", "quelle")
    fdsrc.set_property('location', '/home/dmeyer/stream.dump')

    tssplitter = gst.element_factory_make("tssplitter", "mysplitter")
    tssplitter.set_property('debug-output', True)
    tssplitter.connect("pad-added", onNewPad)

    pipeline = gst.Pipeline("splitterchain")
    pipeline.add(fdsrc, tssplitter)

    fdsrc.link(tssplitter)

    pipeline.set_state(gst.STATE_PLAYING);

    filesinkA = gst.element_factory_make('filesink', 'sinkA')
    filesinkA.set_property('location', '/tmp/filesinkA.ts')
    filesinkA.set_property('sync', '1')
    pipeline.add(filesinkA)
    filtername2obj["myfilter1"] = filesinkA

    filesinkB = gst.element_factory_make('filesink', 'sinkB')
    filesinkB.set_property('location', '/tmp/filesinkB.ts')
    filesinkB.set_property('sync', '1')
    pipeline.add(filesinkB)
    filtername2obj["myfilter2"] = filesinkB


    tssplitter.emit("set-filter", "myfilter2", "386")
    tssplitter.emit("set-filter", "myfilter1", "110,120")

    print "SLEEPING"
    time.sleep(1)
    print "DONE"

#    fdsrc.set_state(gst.STATE_PLAYING);
#    tssplitter.set_state(gst.STATE_PLAYING);
#    filesinkA.set_state(gst.STATE_PLAYING);
#    filesinkB.set_state(gst.STATE_PLAYING);
    mainloop = gobject.MainLoop()

    def bus_event(bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            mainloop.quit()
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            mainloop.quit()           
        return True
    pipeline.get_bus().add_watch(bus_event)

    mainloop.run()
    pipeline.set_state(gst.STATE_NULL)


if __name__ == "__main__":
    main()
