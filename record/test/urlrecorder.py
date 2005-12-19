import sys
import time
import logging
import socket

import kaa
from kaa.notifier import OneShotTimer
from kaa.record import URLDevice, Filewriter, Recording

kaa.base.create_logger()
logging.getLogger('record').setLevel(logging.DEBUG)

dev = URLDevice('channels-url0.conf')

chain = kaa.record.Chain()
chain2 = kaa.record.Chain()
    
if 1:
    chain.append(kaa.record.Filewriter('foo.mpg', 0))
    chain2.append(kaa.record.Filewriter('foo2.mpg', 0))

    # start recording
    # channels 1 and two must belong to the same bouquet in order
    # to record both at the same time.
    idA = dev.start_recording('1', chain)
    idB = dev.start_recording('2', chain2)

    # stop record after 10 seconds
    t = OneShotTimer(dev.stop_recording, idA).start(10)

    # stop record after 20 seconds
    t = OneShotTimer(dev.stop_recording, idB).start(20)

    # stop test after 15 seconds
    t = OneShotTimer(sys.exit, 0).start(22)

kaa.main()
