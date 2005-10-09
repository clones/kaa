import sys
import time
import logging
import kaa.record.v4l_tuner
import kaa.record.v4l_frequencies
from kaa.record.channels import ALL_CHANNELS
import kaa.record._vbi as vbi

DEVICE   = '/dev/video0'
NORM     = 'pal'
CHANLIST = 'europe-west'

x = kaa.record.v4l_tuner.V4L(DEVICE, NORM, CHANLIST)
x.setinput(0)
x.print_settings()

data = vbi.VBI()
channels = []

frequencies = [ 'SE20', 'S40', 'E8', '39', 'E9']
frequencies = kaa.record.v4l_frequencies.CHANLIST[CHANLIST]

print
print 'start channel scan'
for k in frequencies:
    x.setchannel(k)
    time.sleep(0.5)
    data.reset()
    print 'scan %-5s...' % k,
    sys.__stdout__.flush()

    if x.gettuner(0)['signal']:
        sys.__stdout__.flush()
        time.sleep(0.25)
        for i in range(100):
            data.read_sliced()
            if data.network:
                for chanid, v4lid, dvbid in ALL_CHANNELS:
                    if data.network[1] in v4lid:
                        print chanid
                        break
                else:
                    print 'unkown network "%s" (%s)' % data.network
                    chanid = data.network[0]
                break
        else:
            print 'unkown network "%s"' % k
            chanid = k
        freq = kaa.record.v4l_frequencies.get_frequency(k, CHANLIST)
        channels.append((freq, chanid))
    else:
        print 'no channel'

print
print 'Found the following channels:'
for freq, name in channels:
    print '  %20s on freq %s' % (name, freq)
