import kaa.vfs
import sys
import os
import kaa
import time

def msg(*args):
    print '>>>>>>>>>', args
    
kaa.vfs.connect(os.path.expanduser("~/.vfs"))

a = u'Inkubus Sukkubus'
#a = u'Bif Naked'

t1 = time.time()
result = kaa.vfs.get(sys.argv[1]).listdir()
# result = kaa.vfs.query(artist=a)
# result = kaa.vfs.query(attr='album', type='audio')
t2 = time.time()

result.signals['changed'].connect(msg, 'changed')
result.signals['progress'].connect(msg, 'progress')
result.signals['up-to-date'].connect(msg, 'up-to-date')

result.monitor()

print 'query took', (t2 - t1)

print result[0].getattr('foo')
result[0].setattr('foo', 'barw')

if 1:
    for r in result:
        print r

print 'loop'
kaa.main()
