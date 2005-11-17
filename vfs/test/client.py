import kaa.vfs.client
from kaa.notifier import Timer, OneShotTimer
import sys
import kaa
import kaa.notifier
from kaa.base.weakref import weakref
import time

def foo():
    print 'delete all'
    global q
    q = None

def progress(pos, max):
    print 'progress', pos, max

def update(query):
    items = query.get()
    print 'update'
    for item in items:
        print item

def show_artists_list():
    for artist in c.query(attr='artist', type='audio').get():
        print artist
        for album in c.query(attr='album', artist=artist, type='audio').get():
            print ' ', album
        
c = kaa.vfs.client.Client('vfsdb')
t1 = time.time()
q = c.query(dirname='/home/dmeyer/images/intership/eemshaven/mager/')
#q = c.query(dirname='/home/dmeyer/video')
q.signals['changed'].connect(update, weakref(q))
q.signals['progress'].connect(progress)
t2 = time.time()
q.get()
t3 = time.time()
for item in q.get():
    print item

print 'q took %s' % (t2 - t1), (t3 - t1)

#OneShotTimer(show_artists_list).start(1)
#Timer(foo).start(5)
print 'loop'
kaa.main()
