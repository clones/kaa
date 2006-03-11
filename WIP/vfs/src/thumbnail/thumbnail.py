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
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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

__all__ = [ 'Thumbnail', 'NORMAL', 'LARGE' ]

NORMAL  = 'normal'
LARGE   = 'large'

# python imports
import os
import md5
import logging

# kaa imports
from kaa import ipc
from kaa.weakref import weakref
from kaa.notifier import Signal, step

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
        self.signal = Signal()
        self.finished = False
        Job.all.append(self)
        

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
        _schedule((_client_id, Thumbnail.next_id), self.name,
                  self._thumbnail % type, SIZE[type],
                  __ipc_oneway=True, __ipc_noproxy_args=True)

        job = Job(self, Thumbnail.next_id)

        if not wait:
            return job.signal

        while not job.finished:
            step()

    image = property(get, set, None, "thumbnail image")
    failed = property(is_failed, set, None, "return True if thumbnailing failed")

    
def _callback(id, *args):
    if not id:
        for i in args[0]:
            log.error(i)
        return

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
            _remove((_client_id, job.id), __ipc_oneway=True, __ipc_noproxy_args=True)


# connect to ipc
_server = os.path.join(os.path.dirname(__file__), 'server.py')
_server = ipc.launch(_server, 5, ipc.IPCClient, 'thumb/socket').get_object('thumb')

_client_id = _server.connect(_callback)
_schedule = _server.schedule
_remove = _server.remove
