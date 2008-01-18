# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# thumbnail.py - client part for thumbnailing
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'Thumbnail', 'NORMAL', 'LARGE', 'SUPPORT_VIDEO', 'connect' ]

NORMAL  = 'normal'
LARGE   = 'large'

PRIORITY_HIGH   = 0
PRIORITY_NORMAL = 1
PRIORITY_LOW    = 2

# python imports
import os
import md5
import time
import logging
import stat
import socket

# kaa imports
import kaa
import kaa.rpc
from kaa.weakref import weakref
import kaa.metadata

# kaa.thumb imports
from _libthumb import png

# get logging object
log = logging.getLogger('beacon.thumb')

# sizes for the thumbnails
SIZE = { NORMAL: (128, 128), LARGE: (256, 256) }

SUPPORT_VIDEO = False
for path in os.environ.get('PATH').split(':'):
    if os.path.isfile(path + '/mplayer'):
        SUPPORT_VIDEO = True

class Job(object):

    all = []

    def __init__(self, job, id, priority):
        self.valid = weakref(job)
        self.id = id
        self.priority = priority
        self.signal = kaa.Signal()
        Job.all.append(self)

_client = None

class Thumbnail(object):

    next_id = 0

    def __init__(self, name, media, url=None):
        self.name = os.path.realpath(name)
        self.destdir = media.thumbnails

        if not url:
            # create url to be placed in the thumbnail
            # FIXME: handle media.mountpoint
            url = 'file://' + os.path.normpath(name)
        self.url = url

        # create digest for filename (with %s for the size)
        self._thumbnail = media.thumbnails + '/%s/' + md5.md5(url).hexdigest()


    def get(self, type='any', check_mtime=False):
        if check_mtime:
            image = self.get(type)
            if image:
                metadata = kaa.metadata.parse(image)
                if metadata:
                    mtime = metadata.get('Thumb::MTime')
                    if mtime == str(os.stat(self.name)[stat.ST_MTIME]):
                        return image
            # mtime check failed, return no image
            return None

        if type == 'any':
            image = self.get(LARGE, check_mtime)
            if image:
                return image
            type = NORMAL
        if os.path.isfile(self._thumbnail % type + '.png'):
            return self._thumbnail % type + '.png'
        if os.path.isfile(self._thumbnail % type + '.jpg'):
            return self._thumbnail % type + '.jpg'
        if not type == 'fail/beacon':
            return self.get('fail/beacon', check_mtime)
        return None


    def set(self, image, type='both'):
        if type == 'both':
            self.set(image, NORMAL)
            self.set(image, LARGE)
            return

        dest = '%s/%s' % (self.destdir, type)

        i = self._thumbnail % type + '.png'
        png(self.name, i, SIZE[type], image._image)
        log.info('store %s', i)


    def exists(self, check_mtime=False):
        return self.get(NORMAL, check_mtime) or self.get(LARGE, check_mtime) \
               or self.get('fail/beacon', check_mtime)


    def is_failed(self):
        return self.get('fail/beacon')


    def create(self, type=NORMAL, priority=PRIORITY_NORMAL):
        Thumbnail.next_id += 1

        dest = '%s/%s' % (self.destdir, type)
        if not os.path.isdir(dest):
            os.makedirs(dest, 0700)

        # schedule thumbnail creation
        _client.schedule(Thumbnail.next_id, self.name,
                         self._thumbnail % type, SIZE[type], priority)

        job = Job(self, Thumbnail.next_id, priority)
        return job.signal


    image  = property(get, set, None, "thumbnail image")
    failed = property(is_failed, set, None, "true if thumbnailing failed")



class Client(object):

    def __init__(self):
        self.id = None
        server = kaa.rpc.Client('thumb/socket')
        server.connect(self)
        self._schedules = []
        self.rpc = server.rpc


    def schedule(self, id, filename, imagename, type, priority):
        if not self.id:
            # Not connected yet, schedule job later
            self._schedules.append((id, filename, imagename, type, priority))
            return

        # server rpc calls
        self.rpc('schedule', (self.id, id), filename, imagename, type, priority)


    @kaa.rpc.expose('connect')
    def _server_callback_connected(self, id):
        self.id = id
        for s in self._schedules:
            self.schedule(*s)
        self._schedules = []


    @kaa.rpc.expose('log.info')
    def _server_callback_debug(self, *args):
        log.info(*args)


    @kaa.rpc.expose('finished')
    def _server_callback_finished(self, id, filename, imagefile):
        log.info('finished job %s->%s', filename, imagefile)
        for job in Job.all[:]:
            if job.id == id:
                # found updated job
                Job.all.remove(job)
                job.signal.emit()
                continue
            if job.valid:
                continue
            # set old jobs to lower priority
            Job.all.remove(job)
            if job.priority != PRIORITY_LOW:
                self.rpc('set_priority', (self.id, job.id), PRIORITY_LOW)


def connect():
    global _client

    if _client:
        return _client

    start = time.time()
    while True:
        try:
            _client = Client()
            return _client
        except kaa.rpc.ConnectError, e:
            if start + 3 < time.time():
                # start time is up, something is wrong here
                raise RuntimeError('unable to connect to thumbnail server')
            time.sleep(0.01)




