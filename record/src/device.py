from kaa.notifier import SocketDispatcher, Timer

# the internal modules
from _dvb import DvbDevice as _DvbDevice

class DvbDevice(object):
    """
    Wrapper for DVB devices.
    """
    def __init__(self, device, channels, prio):
        self._device = _DvbDevice(device, channels, prio);
        # create socket dispatcher
        sd = SocketDispatcher(self._device.read_fd_data)
        # create tuner timer
        t = Timer(self._device.tuner_timer_expired)
        # give both variables to the device
        self._device.connect_to_notifier(sd, t)


    def __getattr__(self, attr):
        if attr in ('get_card_type', 'get_bouquet_list',
                    'start_recording', 'stop_recording'):
            return getattr(self._device, attr)
        return object.__getattr__(self, attr)
