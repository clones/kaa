#!/usr/bin/python
import pygst
pygst.require('0.10')
import gst
import sys
import time

tuner = gst.element_factory_make("dvbtuner", "tuner")

tuner.set_property('debug-output', True)
tuner.set_property('adapter', 0)

frontendlist = [ "QPSK (DVB-S)", "QAM (DVB-C)", "OFDM (DVB-T)", "ATSC" ]
frontendtype = tuner.get_property('frontendtype')
print 'FRONTEND-TYPE: ', frontendlist[ frontendtype ]
print 'FRONTEND-NAME: ', tuner.get_property('frontendname')
print 'HWDECODER?   : ', tuner.get_property('hwdecoder')

if frontendtype != 2:
    print 'the following code supports only DVB-T cards!'
    sys.exit()


# tuning to RTL (hardcoded values! change them!)
# run "gst-inspect dvbtuner" for valid values
tuner.set_property("frequency", 642000000)
tuner.set_property("inversion", 2)
tuner.set_property("bandwidth", 0)
tuner.set_property("code-rate-high-prio", 2)
tuner.set_property("code-rate-low-prio", 0)
tuner.set_property("constellation", 1)
tuner.set_property("transmission-mode", 1)
tuner.set_property("guard-interval", 2)
tuner.set_property("hierarchy", 0)

# add tuner and video pid
tuner.emit("add-pid", 0x151)
tuner.emit("add-pid", 0x152)

# tune to channel
tuner.emit("tune")

while 1:
    time.sleep(1)
    print tuner.get_property("status")

# now tun something like
# cat /dev/dvb/adapter0/dvr0 | mplayer -vf pp=md/de,phase=U -
