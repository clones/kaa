import logging
import os

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
        medialist.connect(self.db, self)
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

        media = self.db.query_media(id, None)[0]
        if not media:
            if not dev.get('volume.is_disc') == True:
                # fake scanning for other media than rom drives
                return self._device_scanned(None, dev)
            # scan the disc in background
            self.rpc('device.scan', self._device_scanned, dev)(id)
            return

        if media['content'] == 'file' and not dev.get('volume.mount_point'):
            # FIXME: mount only on request
            log.info('mount %s', dev.get('block.device'))
            self.mount(id)
            return

        # create overlay directory structure
        for d in ('.thumbnails/large', '.thumbnails/normal', '.thumbnails/fail/kaa'):
            dirname = os.path.join(self.db.dbdir, id, d)
            if not os.path.isdir(dirname):
                os.makedirs(dirname, 0700)

        m = medialist.add(id, dev)
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


    def _device_scanned(self, metadata, dev):

        # FIXME: check if the device is still valid
        # FIXME: handle failed dvd detection
        id = dev.get('beacon.id')
        if dev.get('volume.is_disc') == True and metadata and \
               metadata['mime'] in ('video/vcd', 'video/dvd'):
            # pass rom drive
            type = metadata['mime'][6:]
            log.info('detect %s as %s' % (id, type))
            mid = self.db.add_object("media", name=id, content=type,
                                     beacon_immediately=True)['id']
            # FIXME: better label
            vid = self.db.add_object("video",
                                     name="",
                                     parent=('media', mid),
                                     title=unicode(metadata['label']),
                                     media = mid,
                                     beacon_immediately=True)['id']
            self.db.commit(force=True)
            for track in metadata.tracks:
                self.db.add_object('track_%s' % type, name=str(track.trackno),
                                   parent=('video', vid),
                                   media=mid,
                                   mtime=0,
                                   chapters=track.chapters, audio=len(track.audio),
                                   subtitles=len(track.subtitles))
            self.db.commit()
        else:
            log.info('detect %s as normal filesystem' % id)
            mid = self.db.add_object("media", name=id, content='file',
                                     beacon_immediately=True)['id']
            dir = self.db.add_object("dir",
                                     name="",
                                     parent=('media', mid),
                                     media=mid,
                                     beacon_immediately=True)
            self.db.commit(force=True)
        self._device_add(dev)
