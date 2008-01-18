import sys
import time
import logging

import kaa
from kaa.record import IVTVDevice, Filewriter, Recording

logging.getLogger('record').setLevel(logging.DEBUG)

ivtv = IVTVDevice('/dev/video0', 'NTSC', chanlist='us-cable', bitrate_mode=1, 
                  bitrate=4500000, bitrate_peak=4500000)


# print some debug
ivtv.print_settings()
# ivtv.setchannel("17")

chain = kaa.record.Chain()
chain2 = kaa.record.Chain()
    
def next():
    # start another
    idB = ivtv.start_recording('14', chain2)

    # change the channel after 10 seconds
    t = kaa.OneShotTimer(ivtv.setchannel, '11').start(10)

    # stop record after 20 seconds
    t = kaa.OneShotTimer(ivtv.stop_recording, idB).start(20)

    # stop test after 15 seconds
    t = kaa.OneShotTimer(sys.exit, 0).start(15)


if 1:
    chain.append(kaa.record.Filewriter('foo.mpg', 0))
    chain2.append(kaa.record.Filewriter('foo2.mpg', 0))

    # One way of using the module is to simply start a recording
    # and stop it later.
    
    # start recording
    idA = ivtv.start_recording('17', chain)

    # stop record after 10 seconds
    t = kaa.OneShotTimer(ivtv.stop_recording, idA).start(10)

    # start another after 10 seconds
    t = kaa.OneShotTimer(next).start(11)


if 0:
    chain.append(kaa.record.Filewriter('foo.mpg', 0))

    # A higher level interface are self starting recording objects. They
    # also have signals you can connect to to get notification of start and stop.

    def rec_started(rec):
        print 'I know that the rec started'

    def rec_stopped(rec):
        print 'I know that the rec stopped'
        
    # record from start time in 3 seconds for 5 seconds
    r = Recording(time.time() + 3, time.time() + 8, ivtv, '17', chain)

    # get some notification
    r.signals['start'].connect(rec_started, r)
    r.signals['stop'].connect(rec_stopped, r)

    # stop test after 15 seconds
    t = kaa.OneShotTimer(sys.exit, 0).start(15)

if 0:
    chain.append(kaa.record.UDPSend('127.0.0.1:12345'))

    # start recording
    idA = ivtv.start_recording('17', chain)

    # stop test after 60 seconds
    t = kaa.OneShotTimer(sys.exit, 0).start(60)

kaa.main.run()
