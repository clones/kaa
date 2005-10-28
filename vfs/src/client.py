from kaa.base import ipc
from kaa.notifier import Signal

class Client(object):
    def __init__(self):
        self._ipc = ipc.IPCClient('vfs')
        self._server = self._ipc.get_object('vfs')

    def listdir(self, dirname):
        return self._server.query(dir=dirname)
        
