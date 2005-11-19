import kaa.vfs.client
from kaa.notifier import Timer, OneShotTimer
import sys
import kaa
import kaa.notifier
from kaa.base.weakref import weakref
import time

import logging
kaa.base.create_logger(logging.INFO)

def foo():
    print 'delete all'
    global q
    q = None

def progress(pos, max, last):
    print 'progress (%s of %s) -- %s' % (pos, max, last)

def update(query):
    print 'update'
    items = query.get()
    for item in items:
        print '..', item

def show_artists_list():
    for artist in c.query(attr='artist', type='audio').get():
        print artist
        for album in c.query(attr='album', artist=artist, type='audio').get():
            print ' ', album
        
c = kaa.vfs.client.Client('vfsdb')
t1 = time.time()
#q = c.query(dirname='/home/dmeyer/images/intership/eemshaven/mager/')
q = c.query(dirname='/home/dmeyer/video')
# q = c.query(files=('/home/dmeyer/video/qt/',
#                    '/home/dmeyer/mp3/Amy_Ray-Covered_For_You.mp3',
#                    '/home/dmeyer/../dmeyer/video/tributefullvid_300.wmv'))
q.signals['changed'].connect(update, weakref(q))
q.signals['progress'].connect(progress)
t2 = time.time()
q.get()
t3 = time.time()
refs = []
for item in q.get():
    print item
    if item.isdir:
        x = item.listdir()
        refs.append(x)
        for s in x.get():
            print '', s
        
print 'q took %s' % (t2 - t1), (t3 - t1)

OneShotTimer(show_artists_list).start(1)
#Timer(foo).start(5)
print 'loop'
kaa.main()
