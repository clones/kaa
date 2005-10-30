import kaa.vfs.client
from kaa.notifier import Timer
import sys
import kaa
import time

def foo():
    print 'delete all'
    global l
    l = None

def progress(pos, max):
    print pos, max
    
c = kaa.vfs.client.Client()
t1 = time.time()
l = c.listdir('/home/dmeyer/images/eemshaven/mager')
t2 = time.time()
print 'client thinks query took %s for %s items' % (t2 - t1, len(l.items))
#print l
#for i in l.items:
#    print i
#l.update(__ipc_async = foo)
print 'done'
#l.signals['progress'].connect(progress)

#print l.update()

# Timer(foo).start(5)
print 'loop'
kaa.main()
