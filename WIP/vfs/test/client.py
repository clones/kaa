import kaa.vfs
from kaa.notifier import Timer, OneShotTimer
import sys
import kaa
import kaa.notifier
from kaa.base.weakref import weakref
import time

import logging

def msg(*args):
    print '>>>>>>>>>', args
    
c = kaa.vfs.connect('vfsdb')
video = c.get(sys.argv[1])
print video
x = video.listdir()

x.signals['changed'].connect(msg, 'changed')
x.signals['progress'].connect(msg, 'progress')
x.signals['up-to-date'].connect(msg, 'up-to-date')

x.monitor()
for f in x:
    print repr(f)

# OneShotTimer(x.monitor, False).start(1)
print 'loop'
kaa.main()
