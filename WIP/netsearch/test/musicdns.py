import sys

import kaa
from kaa.netsearch.musicdns import MusicDNS

def completed(result):
    puid, results = result
    print 'puid:', puid
    for title, artist, length, album, ASIN in results:
        print
        print title
        print artist
        print length
        print album
        print ASIN
    kaa.shutdown()
    
def exception(ex):
    print 'error:', ex
    kaa.shutdown()
    
# client key and version, do not use this one, get
# one for free at www.musicdns.org
cid = '8f46f5f52a5274cdea41eef40982c511'
cvr = '0.1'

dns = MusicDNS(cid, cvr)
dns.signals['completed'].connect_once(completed)
dns.signals['exception'].connect_once(exception)
dns.search(sys.argv[1])

kaa.main()
