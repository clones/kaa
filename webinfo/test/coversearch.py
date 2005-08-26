
from kaa import main
from kaa.webinfo.audio.cdcover import CDCoverGrabber

def exception(e):
    print e

def done(results):
    for r in results:
        print r
        print

def print_status(s):
    print s
    
def print_progress(pos, length):
    if length:
        print pos, length, 100 * float(pos) / length
    else:
        print pos, length

def start_next_search(*args):
    i.search_by_keyword('Enya Only', 'music')

i = CDCoverGrabber()
i.signals['completed'].connect(done)
i.signals['exception'].connect(exception)
i.signals['progress'].connect(print_progress)
i.signals['status'].connect(print_status)

i.signals['completed'].connect_once(start_next_search)

i.search_by_artist('Enya')



main()
