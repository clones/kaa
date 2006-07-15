import sys

import logging
import kaa.rpc

import kaa.notifier
import kaa.metadata

try:
    import hal
except ImportError:
    hal = None

try:
    import cdrom
except ImportError:
    cdrom = None

# get logging object
log = logging.getLogger('beacon.hwmon')

class Server(object):

    def __init__(self):
        log.info('start hardware monitor')
        self.master = None
        self.rpc = None
        self.devices = {}
        self._ipc = kaa.rpc.Server('hwmon')
        self._ipc.signals['client_connected'].connect_once(self.client_connect)
        self._ipc.connect(self)
        if hal:
            hal.signals['failed'].connect(self._hal_failure)
            self._start_service(hal)
        elif cdrom:
            self._start_service(cdrom)


    def _start_service(self, service):
        service.signals['add'].connect(self._device_new)
        service.signals['remove'].connect(self._device_remove)
        service.signals['changed'].connect(self._device_changed)
        service.start()
        

    def _hal_failure(self, reason):
        log.error(reason)
        if cdrom:
            self._start_service(cdrom)
            

    # -------------------------------------------------------------------------
    # Client handling
    # -------------------------------------------------------------------------

    def client_connect(self, client):
        """
        Connect a new client to the server.
        """
        log.info('beacon <-> hwmon connected')
        self.master = client

            
    # -------------------------------------------------------------------------
    # Device handling
    # -------------------------------------------------------------------------

    def _device_new(self, dev):
        if dev.prop.get('volume.uuid'):
            dev.prop['beacon.id'] = str(dev.prop.get('volume.uuid'))
        else:
            log.error('impossible to find unique string for beacon.id')
            return True

        # FIXME: add a nice title
        
        self.devices[dev.get('beacon.id')] = dev
        if not self.rpc:
            return True
        self.rpc('device.add', dev.prop)
        
        
    def _device_remove(self, dev):
        del self.devices[dev.get('beacon.id')]
        if not self.rpc:
            return True
        self.rpc('device.remove', dev.prop.get('beacon.id'))

        
    def _device_changed(self, dev, prop):
        if not self.rpc:
            return True
        prop['beacon.id'] = dev.prop.get('beacon.id')
        self.rpc('device.changed', dev.prop.get('beacon.id'), prop)


    # -------------------------------------------------------------------------
    # External RPC API
    # -------------------------------------------------------------------------

    @kaa.rpc.expose('connect')
    def connect(self):
        self.rpc = self.master.rpc
        for dev in self.devices.values():
            self.rpc('device.add', dev.prop)


    @kaa.rpc.expose('shutdown')
    def shutdown(self):
        sys.exit(0)


    @kaa.rpc.expose('device.scan')
    def scan(self, id):
        dev = self.devices.get(id)
        if not dev:
            return None
        # FIXME: we don't the scanning in a thread, this could block.
        # But it shouldn't matter, but check that.
        return kaa.metadata.parse(dev.get('block.device'))


    @kaa.rpc.expose('device.mount')
    def mount(self, id):
        dev = self.devices.get(id)
        if not dev:
            return None
        dev.mount()
        
