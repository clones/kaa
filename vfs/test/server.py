import kaa.vfs.server
from kaa.notifier import Timer
import kaa
import gc

def do_gc():
    g = gc.collect()
    if g:
        print 'gc: deleted %s objects' % g
    if gc.garbage:
        print 'gc: found %s garbage objects' % len(gc.garbage)
        for g in gc.garbage:
            print g
    return True

Timer(do_gc).start(1)
kaa.main()
