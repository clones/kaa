from kaa.notifier import OneShotTimer

import parser

class Notification(object):
    def __init__(self, remote, id):
        self.remote = remote
        self.id = id

    def __call__(self, *args, **kwargs):
        self.remote(self.id, __ipc_oneway=True, *args, **kwargs)
        

class Monitor(object):
    """
    Monitor query for changes and call callback.
    """
    NEXT_ID = 1
    def __init__(self, callback, db, query):
        self.id = Monitor.NEXT_ID
        Monitor.NEXT_ID += 1
        self.callback = Notification(callback, self.id)

        self._db = db
        self._query = query

        items = []
        for item in self._db.query(**query).get():
            mtime = parser.get_mtime(item)
            if not mtime:
                continue
            if isinstance(item.data, dict) and item.data['mtime'] == mtime:
                continue
            items.append(item)
        if items:
            parser.Checker(self._db, items, self.callback)
        else:
            # do this later to make sure the monitor is known to
            # the remote side
            OneShotTimer(self.callback, 'progress', 0, 0).start(0)
            
    def __del__(self):
        print 'delete monitor', self._query


