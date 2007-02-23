#!/usr/bin/python
import pygst
pygst.require('0.10')
import gst
import sys
import time
import gc
import logging

# import kaa.notifier and set mainloop to glib
import kaa.notifier
kaa.notifier.init('gtk', x11=False)

import kaa.record2

logging.getLogger('record').setLevel(logging.INFO)
logging.getLogger('record.channel').setLevel(logging.ERROR)

# test app logic

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

def tuner_debug(dvb):
    print dvb._tuner.get_property('status')

def gc_check():
    gc.collect()
    for g in gc.garbage:
        print 'oops', g

if len(sys.argv) < 3:
    print 'syntax: %s <channels.conf> <channelname>' % sys.argv[0]
    sys.exit()

ccr = kaa.record2.ConfigFile( sys.argv[1] )
chan = ccr.get_channel( sys.argv[2] )
if not chan:
    print 'cannot find channel', sys.argv[2]
    sys.exit()
    
print chan.config
print 'using channel config of %s' % sys.argv[1]
print 'and searching channel %s' % sys.argv[2]

device = kaa.record2.Device('dvb0')

kaa.record2.Recording(time.time() + 3, time.time() + 8, device,
                      chan, kaa.record2.Filewriter('zdf.ts'))
kaa.notifier.Timer(tuner_debug, device.device).start(1)

# # start 3sat in 3 seconds
# kaa.notifier.OneShotTimer(create_recording, '3sat.ts', 561, 562).start(3)
# # start second ZDF recording in 5 seconds
# kaa.notifier.OneShotTimer(create_recording, 'zdf2.ts', 545, 546).start(5)
# # stop first ZDF recording 5 seconds later

kaa.notifier.Timer(gc_check).start(1)
kaa.notifier.loop()
