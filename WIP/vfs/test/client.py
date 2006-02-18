import kaa.vfs
import sys
import kaa
import time

def msg(*args):
    print '>>>>>>>>>', args
    
kaa.vfs.connect('vfsdb')

a = u'Inkubus Sukkubus'
#a = u'Bif Naked'

t1 = time.time()
result = kaa.vfs.get(sys.argv[1]).listdir()
# result = kaa.vfs.query(artist=a)
# result = kaa.vfs.query(attr='album', type='audio')
t2 = time.time()

# x.signals['changed'].connect(msg, 'changed')
# x.signals['progress'].connect(msg, 'progress')
# x.signals['up-to-date'].connect(msg, 'up-to-date')

# x.monitor()

print 'query took', (t2 - t1)

if 1:
    for r in result:
        print r

print 'loop'
kaa.main()
