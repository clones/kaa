from kaa.beacon.inotify import INotify
import kaa, os

def cb(mask, name):
    if mask & INotify.CREATE:
        print name, "created."
    elif mask & INotify.CHANGE:
        print name, "changed."
    elif mask & INotify.DELETE:
        print name, "deleted"

i = INotify()
dir = os.path.expanduser("~")
i.watch(dir).connect(cb)
print "Now monitoring", dir
kaa.main.run()
