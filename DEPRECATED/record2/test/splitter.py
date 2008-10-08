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

def probe(*args):
    print args

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
    sink = filtername2obj[pad.get_name()].get_pad('sink')
    pad.link(sink)
    # sink.add_data_probe(probe)
    print "---"


def add_filesink(pipeline, tssplitter, filename, pids):
#    pipeline.set_state(gst.STATE_PAUSED);
    sink = gst.element_factory_make('filesink')
    sink.set_property('location', filename)
    name = sink.get_name()
    filtername2obj[name] = sink
    pipeline.add(sink)
    tssplitter.emit("set-filter", name, pids)
    sink.set_state(gst.STATE_PLAYING)
#    pipeline.set_state(gst.STATE_PLAYING);

    
def main():
    global foo

    mainloop = gobject.MainLoop()
    def bus_event(bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
	    print 'EOS'
            mainloop.quit()
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            mainloop.quit()           
	print message
        return True

    pipeline = gst.Pipeline("splitterchain")
    pipeline.get_bus().add_watch(bus_event)

    fdsrc = gst.element_factory_make("filesrc", "quelle")
    fdsrc.set_property('location', '/home/dmeyer/zdf.ts')

    tssplitter = gst.element_factory_make("tssplitter", "mysplitter")
    tssplitter.set_property('debug-output', True)
    tssplitter.connect("pad-added", onNewPad)

    pipeline.add(fdsrc, tssplitter)

    fdsrc.link(tssplitter)

    pipeline.set_state(gst.STATE_PLAYING);

    # add_filesink(pipeline, tssplitter, '/tmp/filesinkA.ts', '110,120')
    # add_filesink(pipeline, tssplitter, '/tmp/filesinkB.ts', '10')

    add_filesink(pipeline, tssplitter, '/tmp/filesinkA.ts', '110,120')
    add_filesink(pipeline, tssplitter, '/tmp/filesinkB.ts', '110')

    mainloop.run()
    pipeline.set_state(gst.STATE_NULL)


if __name__ == "__main__":
    main()
