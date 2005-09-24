import os, sys, struct, fcntl, select, array
from kaa import notifier

class INotify:
    IOCTL_WATCH = -2146938623
    IOCTL_IGNORE = -2147200766

    IN_MODIFY = 0x00000002
    IN_ATTRIB = 0x00000004
    IN_DELETE_SUBDIR = 0x00000100
    IN_DELETE_FILE = 0x00000200
    IN_CREATE_SUBDIR = 0x00000400
    IN_CREATE_FILE = 0x00000800
    IN_DELETE_SELF = 0x00001000
    IN_UNMOUNT = 0x00002000

    EV_CREATED_FILE = IN_CREATE_FILE
    EV_CREATED_DIR = IN_CREATE_SUBDIR
    EV_CREATED = IN_CREATE_FILE | IN_CREATE_SUBDIR
    EV_DELETED_FILE = IN_DELETE_FILE
    EV_DELETED_DIR = IN_DELETE_SUBDIR
    EV_DELETED = IN_DELETE_FILE | IN_DELETE_SUBDIR
    EV_CHANGED = IN_MODIFY | IN_ATTRIB

    WATCH_MASK = IN_MODIFY | IN_ATTRIB | IN_DELETE_SUBDIR | IN_DELETE_FILE | \
                 IN_CREATE_SUBDIR | IN_CREATE_FILE | IN_DELETE_SELF | IN_UNMOUNT

    def __init__(self):
        self.signals = {
            "event": notifier.Signal()
        }

        self._fd = os.open("/dev/inotify", os.O_RDONLY)
        self._watches = {}
        self._read_buffer = ""
        self._dispatcher = notifier.WeakSocketDispatcher(self._handle_data)
        self._dispatcher.register(self._fd)
    
    def __del__(self):
        os.close(self._fd)
        self._dispatcher.unregister()

    def watch(self, path, callback = None):
        fd = os.open(path, os.O_RDONLY)
        args = struct.pack("LL", fd, INotify.WATCH_MASK)
        args = array.array("c", args)
        wd  = fcntl.ioctl(self._fd, INotify.IOCTL_WATCH, args, True)
        self._watches[wd] = [path, callback, 0]
        os.close(fd)

    def ignore(self, path):
        for (wd, (watch_path, callback, eat)) in self._watches.items():
            if watch_path == path:
                args = struct.pack("L", wd)
                r = fcntl.ioctl(self._fd, INotify.IOCTL_IGNORE, args)
                del self._watches[wd]

    def _handle_data(self):
        data = os.read(self._fd, 32768)
        self._read_buffer += data
        while 1:
            if len(self._read_buffer) < 16:
                break
            wd, mask, cookie, size = struct.unpack("LLLL", self._read_buffer[0:16])
            if size:
                fname = self._read_buffer[16:16+size]
                fname = fname[:fname.find("\x00")]
            else:
                fname = None

            if wd in self._watches:
                if self._watches[wd][2]:
                    self._watches[wd][2] -= 1
                else:
                    self._handle_event(wd, fname, mask)

            self._read_buffer = self._read_buffer[16+size:]
    

    def _handle_event(self, wd, filename, mask):
        dirname, callback = self._watches[wd][:2]
        if mask & INotify.EV_CREATED_FILE:
            # CREATE events are always followed by CHANGE events.  This isn't
            # strictly necessary, so we increment a counter which will cause
            # the next event to be eaten.
            self._watches[wd][2] += 1

        if mask & (INotify.EV_CREATED | INotify.EV_DELETED | INotify.EV_CHANGED):
            if callback:
                callback(dirname, filename, mask)
            self.signals["event"].emit(dirname, filename, mask)

        if mask & INotify.IN_DELETE_SELF:
            del self.watches[wd]
            self._dispatcher.unregister()



if __name__ == "__main__":
    import kaa

    def cb(dirname, filename, mask):
        if mask & INotify.EV_CHANGED:
            print "CHANGE:", os.path.join(dirname, filename)
        elif mask & INotify.EV_DELETED:
            print "DELETE:", os.path.join(dirname, filename)
        elif mask & INotify.EV_CREATED:
            print "CREATE:", os.path.join(dirname, filename)

    i = INotify()
    i.signals["event"].connect(cb)
    homedir = os.path.expanduser("~")
    print "Monitoring", homedir
    i.watch(homedir)
    kaa.main()
