import sys

import kaa
from kaa.notifier import OneShotTimer
from kaa.record import DvbDevice, Filewriter

dvb = DvbDevice('/dev/dvb/adapter0', '/home/dmeyer/.freevo/channels.conf', 9)

# print some debug
print dvb.get_card_type()
print dvb.get_bouquet_list()

# start recording
id = dvb.start_recording('ZDF', Filewriter('foo.mpg', 0, Filewriter.FT_MPEG))

# stop record after 10 seconds
t = OneShotTimer(dvb.stop_recording, id).start(10000)

# stop test after 15 seconds
t = OneShotTimer(sys.exit, 0).start(15000)

kaa.main()
