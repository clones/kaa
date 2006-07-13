import logging

import kaa.rpc

from media import medialist

# get logging object
log = logging.getLogger('beacon.hwmon')

ADD_DISC_SUPPORT = 1

class Client(object):

    def __init__(self):
        server = kaa.rpc.Client('hwmon')
        server.connect(self)
        self.shutdown = server.rpc('shutdown')
        self.rpc = server.rpc
        self.mount = self.rpc('device.mount')


    def set_database(self, handler, db, rootfs):
        self.db = db
        # handler == beacon.Server
        self.handler = handler
        self.rpc('connect')()
        self._device_add(rootfs)

        
    @kaa.rpc.expose('device.add')
    def _device_add(self, dev):

        # FIXME: check if the device is still valid

        id = dev.get('beacon.id')
        if medialist.get(id):
            # already in db
            media = medialist.get(id)
            media.update(dev)
            self.handler.media_changed(media)
            return

        if not self.db.query_raw(type="media", name=id):
            # FIXME: only scan rom drives
            if not dev.get('block.device'):
                return self._device_scanned(None, dev)
            self.rpc('device.scan', self._device_scanned, dev)(dev.get('beacon.id'))
            return

        # FIXME: rom drives without dir
        if not dev.get('volume.mount_point'):
            # mount first
            log.info('mount %s', dev.get('block.device'))
            self.mount(id)
            return

        # FIXME: create overlay + .thumbnail dirs
        m = medialist.add(id, self.db, self, dev)
        self.handler.media_changed(m)
        return
    

    @kaa.rpc.expose('device.remove')
    def _device_remove(self, id):
        log.info('remove device %s' % id)
        self.handler.media_removed(medialist.get(id))
        medialist.remove(id)


    @kaa.rpc.expose('device.changed')
    def _device_change(self, id, dev):
        log.info('change device %s', id)
        self._device_add(dev)


    def _device_scanned(self, result, dev):

        # FIXME: check if the device is still valid
        
        id = dev.get('beacon.id')
        log.info('create media entry for %s' % id)
        if ADD_DISC_SUPPORT:
            # FIXME: rom drives without dir
            mid = self.db.add_object("media", name=id, content='file',
                                     beacon_immediately=True)['id']
            self.db.add_object("dir", name="", parent=('media', mid),
                               beacon_immediately=True)
            self.db.commit(force=True)
        self._device_add(dev)
