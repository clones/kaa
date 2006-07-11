__all__ = [ 'signals', 'Device' ]

import sys
import os
import time
import signal
import logging

import kaa.notifier

# check for dbus and it's version
import dbus 
if getattr(dbus, 'version', (0,0,0)) < (0,51,0):
    raise ImportError('dbus >= 0.51.0 not found')
import dbus.glib

from utils import fstab

# use gtk main loop
kaa.notifier.init('gtk')

# get logging object
log = logging.getLogger('beacon.hal')

# HAL signals
signals = { 'add': kaa.notifier.Signal(),
            'remove': kaa.notifier.Signal(),
            'changed': kaa.notifier.Signal(),
            'failed': kaa.notifier.Signal()
          }

class Device(object):
    """
    A device object
    """
    def __init__(self, prop, bus):
        self.udi = prop['info.udi']
        self.prop = prop
        self._eject = False
        self._bus = bus
        
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def mount(self, umount=False):
        """
        Mount or umount the device.
        """
        if self.prop.get('volume.mount_point'):
            # already mounted
            return False
        for device, mountpoint, type, options in fstab():
            if device == self.prop['block.device'] and \
                   (options.find('users') >= 0 or os.getuid() == 0):
                cmd = ('mount', self.prop['block.device'])
                if umount:
                    cmd = ('umount', self.prop['block.device'])
                break
        else:
            if umount:
                cmd = ("pumount-hal", self.udi)
            else:
                cmd = ("pmount-hal", self.udi)
        proc = kaa.notifier.Process(cmd)
        proc.signals['stdout'].connect(log.warning)
        proc.signals['stderr'].connect(log.error)
        proc.start()
        return True


    def eject(self):
        """
        Eject the device. This includes umounting and removing from
        the list. Devices that can't be ejected (USB sticks) are only
        umounted and removed from the list.
        """
        if self.prop.get('volume.mount_point'):
            # umount before eject
            self._eject = True
            return self.mount(umount=True)
        # remove from list
        return _device_remove(self.udi)

        
    # -------------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------------

    def _modified (self, num_changes, change_list):
        """
        Device was modified (mount, umount..)
        """
        for c in change_list:
            if c[0] == 'volume.mount_point':
                obj = self._bus.get_object('org.freedesktop.Hal', self.udi)
                obj = dbus.Interface(obj, 'org.freedesktop.Hal.Device')
                obj.GetAllProperties(reply_handler=self._property_update,
                                     error_handler=log.error)


    def _property_update(self, prop):
        """
        Update internal property list and call signal.
        """
        if not prop.get('volume.mount_point') and self._eject:
            self.prop = prop
            return self.eject()
        signals['changed'].emit(self, prop)
        self.prop = prop



# -----------------------------------------------------------------------------
# Connection handling
# -----------------------------------------------------------------------------

_bus = None
_connection_timeout = 2

def _connect_to_hal():
    global _bus
    global _connection_timeout
    _connection_timeout -= 1
    try:
        if not _bus:
            _bus = dbus.SystemBus()
    except Exception, e:
        # unable to connect to dbus
        if not _connection_timeout:
            # give up
            signals['failed'].emit('unable to connect to dbus')
            return False
        kaa.notifier.OneShotTimer(_connect_to_hal).start(1)
        return False
    obj = _bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
    # DONT ASK! dbus sucks!
    kaa.notifier.Timer(_connect_to_hal_because_dbus_sucks, obj).start(0.01)
    return False


def _connect_to_hal_because_dbus_sucks(obj):
    if obj._introspect_state == obj.INTROSPECT_STATE_INTROSPECT_IN_PROGRESS:
        return True
    if obj._introspect_state == obj.INTROSPECT_STATE_DONT_INTROSPECT:
        if not _connection_timeout:
            # give up
            signals['failed'].emit('unable to connect to hal')
            return False
        kaa.notifier.OneShotTimer(_connect_to_hal).start(1)
        return False
    hal = dbus.Interface(obj, 'org.freedesktop.Hal.Manager')
    hal.GetAllDevices(reply_handler=_device_all, error_handler=log.error)
    hal.connect_to_signal('DeviceAdded', _device_new)
    hal.connect_to_signal('DeviceRemoved', _device_remove)
    return False
    

# -----------------------------------------------------------------------------
# Device handling
# -----------------------------------------------------------------------------

_devices = []

#list all devices
def _device_all(device_names):
    #first build list of all Device objects
    for name in device_names:
        obj = _bus.get_object("org.freedesktop.Hal", str(name))
        obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device",
                             reply_handler=_device_add,
                             error_handler=log.error)


def _device_new(udi):
    obj = _bus.get_object("org.freedesktop.Hal", udi)
    obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device",
                         reply_handler=_device_add,
                         error_handler=log.error)
    

#lost device
def _device_remove(udi):
    for dev in _devices:
        if dev.udi == udi:
            break
    else:
        return True
    sig = _bus.remove_signal_receiver
    sig(dev._modified, "PropertyModified", 'org.freedesktop.Hal.Device',
        "org.freedesktop.Hal", udi)
    _devices.remove(dev)
    # signal changes
    signals['remove'].emit(dev)
    

#add new device
def _device_add(prop):
    # only handle mountable devices
    if not "volume.mount_point" in prop:
        return
    if not prop.get('volume.is_disc'):
        # no disc, check if the device is removable
        try:
            fd = open(os.path.dirname(prop["linux.sysfs_path_device"]) + '/removable')
            rm = fd.read(1)
            fd.close()
            if rm != '1':
                # not removable
                return
        except (OSError, KeyError):
            # Error reading info. Either file not found, linux.sysfs_path_device
            # not in prop or no read permissions. So not removable in that case.
            return
    
    dev = Device(prop, _bus)
    _devices.append(dev)
    sig = _bus.add_signal_receiver
    sig(dev._modified, "PropertyModified", 'org.freedesktop.Hal.Device',
        "org.freedesktop.Hal", prop['info.udi'])
    # mount this device, if it is not mounted
    if not prop.get('volume.mount_point'):
        dev.mount()
    # signal changes
    signals['add'].emit(dev)
        


# connect to hal
_connect_to_hal()


if __name__ == '__main__':

    # -------------------------------------------------------------------------
    # Test
    # -------------------------------------------------------------------------

    def changed(dev, prop):
        print "device modified"
        print "    UID: %s" %  dev.udi
        if prop.get('volume.mount_point') == dev.prop.get('volume.mount_point'):
            return
        if prop.get('volume.mount_point'):
            print "    Volume mounted to: %s" %  prop.get('volume.mount_point')
            kaa.notifier.OneShotTimer(dev.eject).start(1)
        else:
            print "    Volume unmounted"
        print
        
    def remove(dev):
        print "lost device"
        print "    UID: %s" % dev.udi
        print


    def add(dev):
        print "\nnew device"
        print "    UID: %s" %  dev.prop['info.udi']
        #product name of the device
        if 'info.product' in dev.prop:
            print "    Product Name: %s" % dev.prop['info.product']
        #manufacturer
        if 'usb_device.vendor' in dev.prop:
            print "    Manufacturer: %s" % dev.prop['usb_device.vendor']
        #serial number
        if 'usb_device.serial' in dev.prop:
            print "    Serial Number: %s" % dev.prop['usb_device.serial']
        #speed (Speed of device, in Mbit/s, in BCD with two decimals)
        if 'usb.speed_bcd' in dev.prop:
            print "    Speed: %s" % dev.prop['usb.speed_bcd']
        #vendor id
        if 'usb.vendor_id' in dev.prop:
            print "    Vendor Id: %s" % dev.prop['usb.vendor_id']
        #product id
        if 'usb_device.product_id' in dev.prop:
            print "    Product Id: %s" % dev.prop['usb_device.product_id']

        #is disc?
        if dev.prop.get('volume.is_disc') == True:
            if 'volume.disc.volume.label' in dev.prop :
                print "    Label: %s" % dev.prop['volume.label']
            if 'volume.disc.type' in dev.prop :
                print "    Type: %s" % dev.prop['volume.disc.type']
            if dev.prop.get('volume.disc.is_videodvd'):
                print "    Disc: Video-DvD"
            if dev.prop.get('volume.disc.is_svcd'):
                print "    Disc: SVCD"
            if dev.prop.get('volume.disc.is_rewritable'):
                print "    Disc is rewritable"
            if dev.prop.get('volume.disc.is_blank'):
                print "    Disc is empty"
            if 'volume.disc.capacity' in dev.prop :
                print "    Capacity: %s" % dev.prop['volume.disc.capacity']

        #usb device?
        if 'info.bus' in dev.prop:
            print "    Hardware: %s" % dev.prop['info.bus']
        #block device
        if 'block.device' in dev.prop:
            print "    Block Device: %s" % dev.prop['block.device']
        #filesystem
        if dev.prop.get('volume.fstype'):
            if dev.prop.get('volume.fsversion'):
                print "    Filesystem: %s , Version: " % \
                      dev.prop['volume.fstype'], dev.prop['volume.fsversion']
            else:
                print "    Filesystem: %s" % dev.prop['volume.fstype']
        #volume uuid
        if 'volume.uuid' in dev.prop:
            print "    Volume UUID: %s" % dev.prop['volume.uuid']
        #mount point
        if dev.prop.get('volume.mount_point'):
            print "    Mount Point: %s" % dev.prop['volume.mount_point']
        else:
            print "    Volume not mounted"
        #volume size
        if 'volume.size' in dev.prop:
            print "    Volume Size: %s" % dev.prop['volume.size']
        print


    def failed(reason):
        print reason

        
    signals['failed'].connect(failed)
    signals['add'].connect(add)
    signals['changed'].connect(changed)
    signals['remove'].connect(remove)
    kaa.notifier.loop()
