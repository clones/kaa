import os

from kaa.base import ipc, weakref
from kaa.base.db import *

from db import Database
from monitor import Monitor

class Server(object):
    def __init__(self, dbdir):
        self._db = Database(dbdir)

        self.register_object_type_attrs("video",
            title = (unicode, ATTR_KEYWORDS),
            width = (int, ATTR_SIMPLE),
            height = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("audio",
            title = (unicode, ATTR_KEYWORDS),
            artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED),
            album = (unicode, ATTR_KEYWORDS),
            genre = (unicode, ATTR_INDEXED),
            samplerate = (int, ATTR_SIMPLE),
            length = (int, ATTR_SIMPLE),
            bitrate = (int, ATTR_SIMPLE),
            trackno = (int, ATTR_SIMPLE))

        self.register_object_type_attrs("image",
            width = (int, ATTR_SEARCHABLE),
            height = (int, ATTR_SEARCHABLE),
            date = (unicode, ATTR_SEARCHABLE))

        # TODO: add more known types

        self._db.commit()
        self._db.wait()

    def register_object_type_attrs(self, *args, **kwargs):
        return self._db.register_object_type_attrs(*args, **kwargs)

    def query(self, *args, **kwargs):
        return self._db.query(*args, **kwargs)

    def monitor(self, callback, **query):
        monitor = Monitor(callback, self._db, query)
        return monitor, monitor.id


_vfs_db = {}

def connect(dbdir):
    dbdir = os.path.normpath(os.path.abspath(dbdir))
    print 'connect to', dbdir

    # TODO: delete databases not used anymore

    if not dbdir in _vfs_db:
        server = Server(dbdir)
        # FIXME: use weakref
        _vfs_db[dbdir] = server
    return _vfs_db[dbdir]

_ipc = ipc.IPCServer('vfs')
_ipc.register_object(connect, 'vfs')
