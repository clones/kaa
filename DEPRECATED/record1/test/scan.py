import sys
import time
import logging
import kaa.record.v4l_tuner
import kaa.record.v4l_frequencies
from kaa.record.channels import ALL_CHANNELS
import kaa.record._vbi as vbi
import kaa.record.v4l_scan

try:
    DEVICE, NORM, CHANLIST = sys.argv[1:]
except:
    print 'usage %s device norm chanlist' % sys.argv[0]
    print 'where'
    print '  device is the video device (e.g. /dev/video0)'
    print '  norm is "pal" or "ntsc"'
    print '  chanlist is one of \n    %s' % \
          '\n    '.join(kaa.record.v4l_frequencies.CHANLIST.keys())
    sys.exit(0)

VBI_DEV = DEVICE.replace('/video', '/vbi')

x = kaa.record.v4l_tuner.V4L(DEVICE, NORM, CHANLIST)
x.setinput(0)
x.print_settings()

data = vbi.VBI(VBI_DEV)
channels = []

frequencies = [ 'SE20', 'S40', 'E8', '39', 'E9']
#frequencies = kaa.record.v4l_frequencies.CHANLIST[CHANLIST]

channels = kaa.record.v4l_scan.scan(x, data, frequencies)

print
print 'Found the following channels:'
for freq, name in channels:
    print '  %20s on freq %s' % (name, freq)
print
print 'Please check if you get correct names and report the result'
print 'back to the freevo-devel mailing list. Thank you.'
