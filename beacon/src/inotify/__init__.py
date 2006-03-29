try:
    from kaa.beacon.inotify import _inotify
except ImportError:
    _inotify = None

import kaa
import os
import struct


class INotify:

    def __init__(self):
        if not _inotify:
            self._fd = -1
            raise SystemError, "INotify support not compiled."

        self.signals = {
            # Master signal: this signal gets emitted on all events.
            "event": kaa.notifier.Signal()
        }

        self._watches = {}
        self._read_buffer = ""

        self._fd = _inotify.init()
        if self._fd < 0:
            raise SystemError, "INotify support not detected on this system."

        self._mon = kaa.notifier.WeakSocketDispatcher(self._handle_data)
        self._mon.register(self._fd)


    def __del__(self):
        if self._fd >= 0:
            os.close(self._fd)
            self._mon.unregister()


    def watch(self, path, mask = None):
        """
        Adds a watch to the given path.  The default mask is anything that
        causes a change (new file, deleted file, modified file, or attribute
        change on the file).  This function returns a Signal that the caller
        can then connect to.  Any time there is a notification, the signal
        will get emitted.  Callbacks connected to the signal must accept 2
        arguments: notify mask and filename.
        """
        if mask == None:
            mask = INotify.WATCH_MASK

        wd = _inotify.add_watch(self._fd, path, mask)
        if wd < 0:
            raise IOError, "Failed to add watch on '%s'" % path

        signal = kaa.notifier.Signal()
        self._watches[wd] = [signal, os.path.realpath(path)]
        return signal


    def ignore(self, path):
        """
        Removes a watch on the given path.
        """
        path = os.path.realpath(path)
        for wd in self._watches:
            if path == self._watches[wd][1]:
                _inotify.rm_watch(self._fd, wd)
                del self._watches[wd]
                return True

        return False

    def _handle_data(self):
        data = os.read(self._fd, 32768)
        self._read_buffer += data

        while True:
            if len(self._read_buffer) < 16:
                break

            wd, mask, cookie, size = struct.unpack("LLLL", self._read_buffer[0:16])
            if size:
                name = self._read_buffer[16:16+size].rstrip('\0')
            else:
                name = None

            self._read_buffer = self._read_buffer[16+size:]
            if wd not in self._watches:
                continue

            path = self._watches[wd][1]
            if name:
                path = os.path.join(path, name)

            self._watches[wd][0].emit(mask, path)
            self.signals["event"].emit(mask, path)

            if mask & INotify.DELETE_SELF:
                # Self got deleted, so remove the watch data.
                del self._watches[wd]


if _inotify:
    # Copy constants from _inotify to INotify
    for attr in dir(_inotify):
        if attr[0].isupper():
            setattr(INotify, attr, getattr(_inotify, attr))

    INotify.WATCH_MASK = INotify.MODIFY | INotify.ATTRIB | INotify.DELETE | \
                         INotify.CREATE | INotify.DELETE_SELF | INotify.UNMOUNT | \
                         INotify.MOVE

    INotify.CHANGE     = INotify.MODIFY | INotify.ATTRIB
    
