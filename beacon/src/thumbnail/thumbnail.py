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

# kaa imports
import kaa
import kaa.rpc
from kaa.weakref import weakref
import kaa.notifier

# kaa.thumb imports
from libthumb import png

# get logging object
log = logging.getLogger('thumb')

# default .thumbnail dir
DOT_THUMBNAIL = os.path.join(os.environ['HOME'], '.thumbnails')

# sizes for the thumbnails
SIZE = { NORMAL: (128, 128), LARGE: (256, 256) }

class Job(object):

    all = []

    def __init__(self, file, id):
        self.file = weakref(file)
        self.id = id
        self.signal = kaa.notifier.Signal()
        self.finished = False
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
        

    def get(self, type='any'):
        if type == 'any':
            image = self.get(LARGE)
            if image:
                return image
            type = NORMAL
        if os.path.isfile(self._thumbnail % type + '.png'):
            return self._thumbnail % type + '.png'
        if os.path.isfile(self._thumbnail % type + '.jpg'):
            return self._thumbnail % type + '.jpg'
        return None


    def set(self, image, type='both'):
        if type in ('both', LARGE):
            png(self.name, self._thumbnail % type + '.png', SIZE[LARGE], image._image)
        if type in ('both', NORMAL):
            png(self.name, self._thumbnail % type + '.png', SIZE[NORMAL], image._image)
            

    def exists(self):
        return self.get(NORMAL) or self.get(LARGE) or self.get('fail/kaa')
    

    def is_failed(self):
        return self._get_thumbnail('fail/kaa')


    def create(self, type=NORMAL, wait=False):
        Thumbnail.next_id += 1
        
        dest = '%s/%s' % (self.destdir, type)
        if not os.path.isdir(dest):
            os.makedirs(dest, 0700)

        # schedule thumbnail creation
        _client.schedule(Thumbnail.next_id, self.name, self._thumbnail % type, SIZE[type])

        job = Job(self, Thumbnail.next_id)

        if not wait:
            return job.signal

        while not job.finished:
            kaa.notifier.step()

    image = property(get, set, None, "thumbnail image")
    failed = property(is_failed, set, None, "return True if thumbnailing failed")



class Client(object):

    def __init__(self):
        self.id = None
        server = kaa.rpc.Client('thumb/socket')
        server.connect(self)
        self.remove = server.rpc('remove')
        self.shutdown = server.rpc('shutdown')
        self._schedule = server.rpc('schedule')
        return


    @kaa.rpc.expose('connect')
    def _connected(self, id):
        self.id = id

        
    def schedule(self, id, *args, **kwargs):
        if not self.id:
            raise AttributeError('thumbnailer not connected')
        self._schedule((self.id, id), *args, **kwargs)
        
        
    def _callback(self, id, *args):
        if not id:
            for i in args[0]:
                log.error(i)

        for job in Job.all[:]:
            if job.id == id:
                log.info('finished job %s->%s', args[0], args[1])
                Job.all.remove(job)
                job.finished = True
                job.signal.emit()
            elif not job.file:
                Job.all.remove(job)
                job.finished = True
                log.info('remove job %s', job.id)
                self.remove((self.id, job.id))


def connect():
    global _client

    if _client:
        return _client
    
    start = time.time()
    while True:
        try:
            _client = Client()
            return _client
        except Exception, e:
            print e
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
