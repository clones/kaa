import kaa.beacon
import sys
import os
import kaa
import time

def msg(*args):
    print 'Beacon Server Message:', args
    
if len(sys.argv) == 1:
    print 'Beacon Test Client'
    print 'Start the client with your query'
    print 'Examples:'
    print '  client.py dirname=/local/video'
    print '  client.py artist=Silbermond'
    print '  client.py attr=album type=audio'
    print '  client.py "keywords=Helden Blind"'
    sys.exit(0)

query = {}
for a in sys.argv[1:]:
    key, value = a.split('=', 1)
    query[key] = value

kaa.beacon.connect(os.path.expanduser("~/.beacon"))

if 'dirname' in query:
    result = kaa.beacon.get(query['dirname']).listdir()
else:
    result = kaa.beacon.query(**query)
    
result.signals['changed'].connect(msg, 'changed')
result.signals['progress'].connect(msg, 'progress')
result.signals['up-to-date'].connect(msg, 'up-to-date')

result.monitor()

if 1:
    for r in result:
        print r

print 'loop'
kaa.main()
