import kaa.beacon
import sys
import os
import kaa
import time

def msg(*args):
    print '>>>>>>>>>', args
    
kaa.beacon.connect(os.path.expanduser("~/.beacon"))

a = u'Inkubus Sukkubus'
#a = u'Bif Naked'

t1 = time.time()
result = kaa.beacon.get(sys.argv[1]).listdir()
# result = kaa.beacon.query(artist=a)
# result = kaa.beacon.query(attr='album', type='audio')
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
