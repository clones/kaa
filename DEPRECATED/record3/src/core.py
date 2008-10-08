import os
import kaa.ioctl as ioctl

from dvb import DVB_T

_devices = None

def get_devices():
    global _devices
    if _devices is not None:
        return _devices
    _devices = {}
    for adapter in range(5):
        frontend = '/dev/dvb/adapter%s/frontend0' % adapter
        if not os.path.exists(frontend):
            continue
        # read frontend0 for aditional information
        INFO_ST = '128s10i'
        val = ioctl.pack( INFO_ST, "", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 )
        devfd = os.open(frontend, os.O_TRUNC)
        r = ioctl.ioctl(devfd, ioctl.IOR('o', 61, INFO_ST), val)
        os.close(devfd)
        val = ioctl.unpack( INFO_ST, r )
        name = val[0].strip()
        if val[1] == 2:
            _devices['dvb%s' % adapter] = DVB_T(adapter)
    return _devices

def get_device(device):
    return get_devices().get(device)
