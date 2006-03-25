import kaa.beacon
import sys
import os
import kaa
import time

def msg(*args):
    print 'Beacon Server Message:', args

def uptodate(stop):
    print 'Beacon has finished the query and parsing'
    if stop:
        sys.exit(0)
        
def progress(cur, total, item):
    n = 0
    if total > 0:
        n = int((cur / float(total)) * 50)
    sys.stdout.write("|%51s| %d / %d\r" % (("="*n + ">").ljust(51), cur, total))
    sys.stdout.flush()
    if cur == total:
        print

if len(sys.argv) == 1:
    print 'Beacon Test Client'
    print 'Start the client with your query'
    print 'Options:'
    print '  --monitor    do not stop but monitor the query for changes'
    print
    print 'Examples:'
    print '  client.py dirname=/local/video'
    print '  client.py --monitor dirname=/local/video'
    print '  client.py artist=Silbermond'
    print '  client.py attr=album type=audio'
    print '  client.py "keywords=Helden Blind"'
    sys.exit(0)

query   = {}
monitor = False
for a in sys.argv[1:]:
    if a == '--monitor':
        monitor = True
        continue
    key, value = a.split('=', 1)
    if key in ('title', 'album', 'artist'):
        value = unicode(value)
    query[key] = value

kaa.beacon.connect(os.path.expanduser("~/.beacon"))

if 'dirname' in query:
    t1 = time.time()
    result = kaa.beacon.get(query['dirname']).listdir()
    t2 = time.time()
else:
    t1 = time.time()
    result = kaa.beacon.query(**query)
    t2 = time.time()

if monitor:
    result.signals['changed'].connect(msg, 'changed')
    result.signals['progress'].connect(progress)
    result.signals['up-to-date'].connect(uptodate, False)
else:
    result.signals['up-to-date'].connect(uptodate, True)
    
result.monitor()

if 1:
    for r in result:
        print r

print 'Query took %s seconds' % (t2-t1)

kaa.main()
