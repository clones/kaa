import sys
import time
import logging

import kaa
from kaa.notifier import OneShotTimer
from kaa.record import DvbDevice, FDSplitter, Filewriter, Recording

dvb = DvbDevice('/dev/dvb/adapter0', '/home/schwardt/.freevo/channels.conf')

splitter = FDSplitter( dvb.get_fd() )
splitter.set_input_type( "TS" )

# print some debug
print dvb.get_card_type()
print dvb.get_bouquet_list()

logging.getLogger('record').setLevel(logging.INFO)

chain = kaa.record.Chain()
chain.append(kaa.record.Remux())
    
if 1:
    chain.append(kaa.record.Filewriter('foo.mpg', 0))

    # One way of using the module is to simply start a recording
    # and stop it later.
    
    # start recording
    idA = dvb.start_recording('ProSieben', chain)
    idB = splitter.add_filter_chain(chain)

    # stop record after 10 seconds
    t = OneShotTimer(dvb.stop_recording, idA).start(10)

    # stop test after 15 seconds
    t = OneShotTimer(sys.exit, 0).start(15)

if 0:
    chain.append(kaa.record.Filewriter('foo.mpg', 0))

    # A higher level interface are self starting recording objects. They
    # also have signals you can connect to to get notification of start and stop.

    def rec_started(rec):
        print 'I know that the rec started'

    def rec_stopped(rec):
        print 'I know that the rec stopped'
        
    # record from start time in 3 seconds for 5 seconds
    r = Recording(time.time() + 3, time.time() + 8, dvb, 'ZDF', chain)

    # get some notification
    r.signals['start'].connect(rec_started, r)
    r.signals['stop'].connect(rec_stopped, r)

    # stop test after 15 seconds
    t = OneShotTimer(sys.exit, 0).start(15)

if 0:
    chain.append(kaa.record.UDPSend('127.0.0.1:12345'))

    # start recording
    idA = dvb.start_recording('ZDF', chain)
    idB = splitter.add_filter_chain(chain)

    # stop test after 60 seconds
    t = OneShotTimer(sys.exit, 0).start(60)

kaa.main()
