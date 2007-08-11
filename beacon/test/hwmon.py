import kaa.notifier

try:
    from kaa.beacon.hwmon import hal
    signals = hal.signals
    print 'Start HAL monitor'
    hal.start()
except ImportError:
    print 'HAL not found'
    hal = None

try:
    from kaa.beacon.hwmon import cdrom
    if not hal:
        signals = cdrom.signals
        print 'Start cdrom monitor'
        cdrom.start()
except ImportError:
    cdrom = None


def hal_failure(reason):
    print 'HAL module start failed:', reason
    if cdrom:
        for sig in cdrom.signals:
            cdrom.signals[sig].connect(hal.signals[sig].emit)
        print 'start plain cdrom module'
        cdrom.start()

if hal and cdrom:
    signals['failed'].connect(hal_failure)
    


def changed(dev, prop):
    print "device modified"
    print "    UID: %s" %  dev.udi
    if prop.get('volume.mount_point') == dev.prop.get('volume.mount_point'):
        return
    if prop.get('volume.mount_point'):
        print "    Volume mounted to: %s" %  prop.get('volume.mount_point')
        kaa.notifier.OneShotTimer(dev.mount, True).start(1)
#             kaa.notifier.OneShotTimer(dev.eject).start(1)
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
            print "    Disc: Video-DVD"
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
    if not dev.prop.get('volume.mount_point'):
        dev.mount()


signals['add'].connect(add)
signals['changed'].connect(changed)
signals['remove'].connect(remove)
kaa.notifier.loop()
