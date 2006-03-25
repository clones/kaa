import os
import sys
import kaa
import kaa.vfs
import logging

# simple connect
kaa.vfs.connect(os.path.expanduser("~/.vfs"))

checked  = []
to_check = []

def progress(cur, total, item):
    n = 0
    if total > 0:
        n = int((cur / float(total)) * 50)
    sys.stdout.write("|%51s| %d / %d\r" % (("="*n + ">").ljust(51), cur, total))
    sys.stdout.flush()
    if cur == total:
        print

def check():
    if to_check:
        d = to_check.pop(0)
        checked.append(d)
        print d.filename
        q = d.listdir()
        q.signals['up-to-date'].connect(next, q)
        q.signals['progress'].connect(progress)
        q.monitor()
    else:
        sys.exit(0)
    
def next(q):
    q.monitor(False)
    for f in q:
        if f._vfs_isdir:
            for i in checked + to_check:
                if f.filename == i.filename:
                    break
            else:
                to_check.insert(0, f)
    check()
    

to_check.append(kaa.vfs.get(sys.argv[1]))

check()

kaa.main()
