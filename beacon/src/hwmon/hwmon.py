import socket
import time

import kaa.notifier
import logging

# get logging object
log = logging.getLogger('beacon.hwmon')


class Mounpoint(object):
    pass

class Client(object):

    def __init__(self):
        self.id = None
        server = kaa.rpc.Client('hwmon')
        server.connect(self)
        self.shutdown = server.rpc('shutdown')
        self.rpc = server.rpc
        

    def set_database(self, db):
        self.db = db
        self.rpc('connect')()

        
    @kaa.rpc.expose('device.add')
    def _device_add(self, dev):
        log.info('new device %s' % dev.get('volume.uuid'))
        log.info('%s', dev)

    @kaa.rpc.expose('device.remove')
    def _device_remove(self, dev):
        log.info('remove device %s' % dev.get('volume.uuid'))
