import logging
import kaa.rpc

import kaa.notifier

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
        self.devices = []
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
        self.devices.append(dev)
        if not self.rpc:
            return True
        self.rpc('device.add')(dev.prop)
        
        
    def _device_remove(self, dev):
        self.devices.remove(dev)
        if not self.rpc:
            return True
        self.rpc('device.remove')(dev.prop)

        
    def _device_changed(self, dev, prop):
        if not self.rpc:
            return True
        self.rpc('device.changed', prop)


    # -------------------------------------------------------------------------
    # External RPC API
    # -------------------------------------------------------------------------

    @kaa.rpc.expose('connect')
    def connect(self):
        self.rpc = self.master.rpc
        for dev in self.devices:
            self.rpc('device.add')(dev.prop)


    @kaa.rpc.expose('shutdown')
    def shutdown(self):
        sys.exit(0)
