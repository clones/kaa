import sys
import time
import logging

import kaa
from kaa.notifier import OneShotTimer
from kaa.record import DvbDevice, Filewriter, Recording

dvb = DvbDevice('/dev/dvb/adapter0', '/home/dmeyer/.freevo/channels.conf', 9)

# print some debug
print dvb.get_card_type()
print dvb.get_bouquet_list()

logging.getLogger('record').setLevel(logging.INFO)

if 0:
    # One way of using the module is to simply start a recording
    # and stop it later.
    
    # start recording
    id = dvb.start_recording('ZDF', Filewriter('foo.mpg', 0, Filewriter.FT_MPEG))

    # stop record after 10 seconds
    t = OneShotTimer(dvb.stop_recording, id).start(10000)


if 1:
    # A higher level interface are self starting recording objects. They
    # also have signals you can connect to to get notification of start and stop.

    def rec_started(rec):
        print 'I know that the rec started'

    def rec_stopped(rec):
        print 'I know that the rec stopped'
        
    # record from start time in 3 seconds for 5 seconds
    r = Recording(time.time() + 3, time.time() + 8, dvb, 'ZDF',
                  Filewriter('foo.mpg', 0, Filewriter.FT_MPEG))

    # get some notification
    r.signals['start'].connect(rec_started, r)
    r.signals['stop'].connect(rec_stopped, r)


# stop test after 15 seconds
t = OneShotTimer(sys.exit, 0).start(15000)

kaa.main()
