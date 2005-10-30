import time
from kaa.base import ipc, weakref
from kaa.notifier import Signal, Callback

class Query(object):
    def __init__(self, query, remote_object):
        self._query = query
        self.remote_object = remote_object
        t1 = time.time()
        self.items = remote_object.execute(__ipc_copy_result=True)
        t2 = time.time()
        print 'init query took %s' % (t2 - t1)
        
    def update(self):
        self.remote_query.update(__ipc_oneway=True)

    def notify(self, event, *args, **kwargs):
        if event == 'progress':
            print 'progress: %s of %s' % (args[0], args[1])
            return
        if event == 'changed':
            print 'remote object changed'
            t1 = time.time()
            self.items = self.remote_object.execute(__ipc_copy_result=True)
            t2 = time.time()
            print 'update query took %s' % (t2 - t1)
            
        
class Client(object):
    def __init__(self):
        self._ipc = ipc.IPCClient('vfs')
        self._server = self._ipc.get_object('vfs')
        self._active_queries = []

    def query(self, **kwargs):
        remote_query = self._server.query(self.notify, **kwargs)
        query = Query(kwargs, remote_query)
        self._active_queries.append(weakref(query))
        return query
        
    def listdir(self, dirname):
        return self.query(dir=dirname)
    
    def notify(self, object, *args, **kwargs):
        for q in self._active_queries:
            if not q:
                continue
            if q.remote_object._query == object:
                q.notify(*args, **kwargs)
                
