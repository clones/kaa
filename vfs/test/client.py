import kaa.vfs.client
from kaa.notifier import Timer, OneShotTimer
import sys
import kaa
import kaa.notifier
from kaa.base.weakref import weakref
import time

import logging
kaa.base.create_logger(logging.INFO)

VERBOSE = True

def foo():
    print 'delete all'
    global q
    q = None

def progress(pos, max, last):
    if VERBOSE:
        print 'progress (%s of %s) -- %s' % (pos, max, last)

def update(client, query):
    print 'update'
    result = query.get()
    if not VERBOSE:
        return
    if isinstance(result, list):
        for item in q.get():
            print item
    else:
        print 'Disc', result, result.item()
        result = result.item()
        if result and result.filename:
            # it is a disc, scan dir (hope it's mounted)
            print 'files on disc (needs to be mounted manually):'
            for f in client.query(dirname=result.filename).get():
                print '    ', f
            print

def show_artists_list():
    for artist in c.query(attr='artist', type='audio').get():
        print artist
        for album in c.query(attr='album', artist=artist, type='audio').get():
            print ' ', album
        
c = kaa.vfs.client.Client('vfsdb')
c.add_mountpoint('/dev/cdrom', '/mnt/cdrom')
c.add_mountpoint('/dev/dvd', '/mnt/dvd')

if len(sys.argv) < 2 or sys.argv[1].find('=') <= 0:
    print 'usage: client query'
    print 'e.g.   client directory=/home/dmeyer/video'
    print '       client file=/path/to/file.mp3'
    print '       client device=/mnt/cdrom'
    print '       client attr=album type=audio'
    sys.exit(0)

if sys.argv[1][:sys.argv[1].find('=')] == 'file':
    t1 = time.time()
    q = c.query(files=(sys.argv[1][sys.argv[1].find('=')+1:],))
else:
    query = {}
    for attr in sys.argv[1:]:
        query[attr[:attr.find('=')]]=attr[attr.find('=')+1:]
    t1 = time.time()
    q = c.query(**query)
q.signals['changed'].connect(update, c, weakref(q))
q.signals['progress'].connect(progress)
t2 = time.time()

result = q.get()
if VERBOSE:
    if isinstance(result, list):
        for item in q.get():
            print item
    else:
        print 'Disc', result

print 'q took %s' % (t2 - t1)

#OneShotTimer(show_artists_list).start(1)
#Timer(foo).start(5)
print 'loop'
kaa.main()
