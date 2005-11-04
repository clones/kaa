from kaa.base import ipc, weakref
from kaa.notifier import Signal

from db import Database

class Query(object):
    def __init__(self, notify, local_db, monitor, query):
        self._query = query
        self._remote = None
        self._result = local_db.query(**query)
        self.id = 0
        monitor(notify, __ipc_async=self._get_monitor, **query)
        self._monitor = None

    def _get_monitor(self, (monitor, id)):
        self._monitor = monitor
        self.id = id
        # FIXME: for some strange reasons, monitor is a ProxiedObject None
        print 'monitor is', monitor, 'id', id
        
    def get(self):
        return self._result.get()

    def notify(self, msg, *args, **kwargs):
        # TODO: redo the query here and emit signals
        print msg, args, kwargs
        
            
class Client(object):
    def __init__(self, db):
        self.monitor = ipc.IPCClient('vfs').get_object('vfs')(db).monitor
        self._db = Database(db)
        self._db.read_only = True
        self._queries = []

    def query(self, **query):
        query = Query(self.notify, self._db, self.monitor, query)
        # TODO: clean up dead weakrefs later
        self._queries.append(weakref(query))
        return query
    
    def notify(self, id, *args, **kwargs):
        for query in self._queries:
            if query and query.id == id:
                query.notify(*args, **kwargs)
                return
        print 'not found'
