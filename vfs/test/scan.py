import kaa.vfs.client
from kaa.notifier import Timer
import sys
import kaa
import kaa.notifier
from kaa.base.weakref import weakref
import time

directories_to_check = []
query = None

def check():
    if not directories_to_check:
        # FIXME: I can't just call exit(0) in a signal based of ipc
        # it will crash the ipc code
        kaa.notifier.OneShotTimer(sys.exit, 0).start(0)
        return
    current = directories_to_check.pop()
    print current
    global query
    # use global query to keep a reference
    query = c.query(dirname=current)
    query.signals['up-to-date'].connect(check)
    # FIXME: needed to get a signal
    query.get()
    
c = kaa.vfs.client.Client('vfsdb')
for path in sys.argv[1:]:
    directories_to_check.append(path)
directories_to_check.reverse()

check()
kaa.main()
