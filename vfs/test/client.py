import kaa.vfs.client
from kaa.notifier import Timer
import sys
import kaa
import kaa.notifier
import time

def foo():
    print 'delete all'
    global l
    l = None

def progress(pos, max):
    print pos, max
    
c = kaa.vfs.client.Client('vfsdb')
t1 = time.time()
#q = c.query(dirname='/home/dmeyer/images/intership/eemshaven/mager/')
q = c.query(dirname='/home/dmeyer/video')
t2 = time.time()
q.get()
t3 = time.time()
for item in q.get():
    print item

print 'q took %s' % (t2 - t1), (t3 - t1)

# t1 = time.time()
# l = c.listdir('/home/dmeyer/images/eemshaven/mager')
# t2 = time.time()
# print 'client thinks query took %s for %s items' % (t2 - t1, len(l.items))
# #print l
# #for i in l.items:
# #    print i
# #l.update(__ipc_async = foo)
# print 'done'
# #l.signals['progress'].connect(progress)

# #print l.update()

# # Timer(foo).start(5)
print 'loop'
kaa.main()
