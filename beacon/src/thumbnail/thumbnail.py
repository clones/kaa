# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# thumbnail.py - Client part for thumbnailing files
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-thumb - Thumbnailing module
# Copyright (C) 2005-2006 Dirk Meyer, et al.
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'Thumbnail', 'NORMAL', 'LARGE', 'connect', 'stop' ]

NORMAL  = 'normal'
LARGE   = 'large'

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
import kaa.notifier
import kaa.metadata

# kaa.thumb imports
from libthumb import png

# get logging object
log = logging.getLogger('beacon.thumb')

# default .thumbnail dir
DOT_THUMBNAIL = os.path.join(os.environ['HOME'], '.thumbnails')

# sizes for the thumbnails
SIZE = { NORMAL: (128, 128), LARGE: (256, 256) }

class Job(object):

    all = []

    def __init__(self, job, id):
        self.valid = weakref(job)
        self.id = id
        self.signal = kaa.notifier.Signal()
        Job.all.append(self)
        

_client = None

class Thumbnail(object):

    next_id = 0

    def __init__(self, name, destdir=DOT_THUMBNAIL, url=None):
        self.name = os.path.realpath(name)
        self.destdir = destdir
        
        if not url:
            # create url to be placed in the thumbnail
            url = 'file://' + os.path.normpath(name)
        self.url = url

        # create digest for filename (with %s for the size)
        self._thumbnail = destdir + '/%s/' + md5.md5(url).hexdigest()
        

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
        return None


    def set(self, image, type='both'):
        if type == 'both':
            self.set(image, NORMAL)
            self.set(image, LARGE)
            return

        dest = '%s/%s' % (self.destdir, type)
        if not os.path.isdir(dest):
            os.makedirs(dest, 0700)

        i = self._thumbnail % type + '.png'
        png(self.name, i, SIZE[type], image._image)
        log.info('store %s', i)


    def exists(self, check_mtime=False):
        return self.get(NORMAL, check_mtime) or self.get(LARGE, check_mtime) \
               or self.get('fail/kaa', check_mtime)
    

    def is_failed(self):
        return self.get('fail/kaa')


    def create(self, type=NORMAL):
        Thumbnail.next_id += 1
        
        dest = '%s/%s' % (self.destdir, type)
        if not os.path.isdir(dest):
            os.makedirs(dest, 0700)

        # schedule thumbnail creation
        _client.schedule(Thumbnail.next_id, self.name,
                         self._thumbnail % type, SIZE[type])

        job = Job(self, Thumbnail.next_id)

    image  = property(get, set, None, "thumbnail image")
    failed = property(is_failed, set, None, "true if thumbnailing failed")



class Client(object):

    def __init__(self):
        self.id = None
        server = kaa.rpc.Client('thumb/socket')
        server.connect(self)
        self._schedules = []

        # server rpc calls
        self.reduce_priority = server.rpc('reduce_priority')
        self.shutdown = server.rpc('shutdown')
        self._schedule = server.rpc('schedule')


    def schedule(self, id, filename, imagename, type):
        if not self.id:
            # Not connected yet, schedule job later
            self._schedules.append((id, filename, imagename, type))
            return
        self._schedule((self.id, id), filename, imagename, type)
        
        
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
            self.reduce_priority((self.id, job.id))


def connect():
    global _client

    if _client:
        return _client
    
    start = time.time()
    while True:
        try:
            _client = Client()
            return _client
        except socket.error, e:
            if start + 3 < time.time():
                # start time is up, something is wrong here
                raise RuntimeError('unable to connect to thumbnail server')
            time.sleep(0.01)

def stop():
    global _client
    
    if not _client:
        return

    _client.shutdown()
    kaa.notifier.step()
    _client = None
