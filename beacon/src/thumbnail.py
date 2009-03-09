# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# thumbnail.py - client part for thumbnailing
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon - A virtual filesystem with metadata
# Copyright (C) 2006-2009 Dirk Meyer
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

__all__ = [ 'Thumbnail', 'SUPPORT_VIDEO', 'connect' ]

NORMAL  = 'normal'
LARGE   = 'large'

# python imports
import os
import md5
import time
import logging
import stat

# kaa imports
import kaa
import kaa.rpc
from kaa.weakref import weakref
from kaa.utils import property
import kaa.metadata

# kaa.thumb imports
import libthumb

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
    """
    Thumbnail handling. This objects is a wrapper for full size image path names.
    """
    # priority for creating
    PRIORITY_HIGH   = 0
    PRIORITY_NORMAL = 1
    PRIORITY_LOW    = 2

    # sizes
    NORMAL = 'normal'

    _next_id = 0

    def __init__(self, name, media, url=None):
        """
        Create Thumbnail handler

        @param name: full, absolute path name of the image file
        @param media: beacon Media object to determine the thumbnailing directory
        @param url: url to store in the thumbnail
        """
        if not name.startswith('/'):
            # FIXME: realpath should not be needed here because
            # beacon itself should take care of it.
            name = os.path.abspath(name)
        self.name = name
        self.destdir = media.thumbnails
        # create url to be placed in the thumbnail
        # os.path.normpath(name) should be used but takes
        # extra CPU time and beacon should always create
        # a correct path
        # FIXME: handle media.mountpoint
        self.url = url or 'file://' + name
        # create digest for filename (with %s for the size)
        self._thumbnail = media.thumbnails + '/%s/' + md5.md5(self.url).hexdigest() + '.png'

    def _get_thumbnail(self, type='any', check_mtime=False):
        """
        Get the filename to the thumbnail. DO NOT USE OUTSIDE OF BEACON

        :param type: 'normal', 'large' or 'any'
        :param check_mtime: Check the file modification time against the information
            stored in the thumbnail. If the file has changed, the thumbnail will not be
            returned.
        :returns: full path to thumbnail file or None
        """
        if check_mtime:
            image = self._get_thumbnail(type)
            if image:
                metadata = kaa.metadata.parse(image)
                if metadata:
                    mtime = metadata.get('Thumb::MTime')
                    if mtime == str(os.stat(self.name)[stat.ST_MTIME]):
                        return image
            # mtime check failed, return no image
            return None
        if type == 'any':
            image = self._get_thumbnail(LARGE, check_mtime)
            if image:
                return image
            type = NORMAL
        if os.path.isfile(self._thumbnail % type):
            return self._thumbnail % type
        if not type == 'fail/beacon':
            return self._get_thumbnail('fail/beacon', check_mtime)
        return None

    def _set_thumbnail(self, image, type='both'):
        """
        Set the thumbnail. DO NOT USE OUTSIDE OF BEACON

        :param image: Image containing the thumbnail
        :type image: kaa.Imlib2 image object
        :param type: 'normal', 'large', or 'both'
        """
        if type == 'both':
            self._set_thumbnail(image, NORMAL)
            return self._set_thumbnail(image, LARGE)
        dest = '%s/%s' % (self.destdir, type)
        i = self._thumbnail % type
        libthumb.png(self.name, i, SIZE[type], image._image)
        log.info('store %s', i)

    @property
    def needs_update(self):
        """
        Check if the image needs an update
        """
        return not self.failed and (not self._get_thumbnail(NORMAL, True) or not self._get_thumbnail(LARGE, True))

    @property
    def normal(self):
        """
        The normal thumbnail
        """
        return self._get_thumbnail(NORMAL)

    @normal.setter
    def normal(self, image):
        """
        The normal thumbnail
        """
        return self._set_thumbnail(image, NORMAL)

    @property
    def large(self):
        """
        The large thumbnail
        """
        return self._get_thumbnail(LARGE)

    @large.setter
    def large(self, image):
        """
        The large thumbnail
        """
        return self._set_thumbnail(image. LARGE)

    @property
    def failed(self):
        """
        Check if thumbnailing failed before. Failed attempts are stored in the
        fail/beacon subdirectory.
        """
        return self._get_thumbnail('fail/beacon')

    @property
    def image(self):
        """
        Get the image, no matter if large or normal
        """
        return self._get_thumbnail()

    @image.setter
    def image(self, image):
        """
        Get the image, no matter if large or normal
        """
        return self._set_thumbnail(image)

    def create(self, priority=None):
        """
        Create a thumbnail.

        :param priority: priority how important the thumbnail is. The thumbnail
            process will handle the thumbnail generation based on this priority.
            If you loose all references to this thumbnail object, the priority will
            automatically set to the lowest value (2). Maximum value is 0, default 1.
        """
        if priority is None:
            priority = Thumbnail.PRIORITY_NORMAL
        Thumbnail._next_id += 1
        # schedule thumbnail creation
        _client.schedule(Thumbnail._next_id, self.name, self._thumbnail, priority)
        job = Job(self, Thumbnail._next_id, priority)
        return job.signal


class Client(object):

    def __init__(self):
        self.id = None
        self._schedules = []

    @kaa.coroutine()
    def connect(self):
        start = time.time()
        while True:
            try:
                channel = kaa.rpc.connect('thumb/socket')
                channel.register(self)
                self.rpc = channel.rpc
                yield kaa.inprogress(channel)
                yield None
            except Exception, e:
                # FIXME: rather than this kludge, catch only the exceptions likely to happen
                # if connection to thumbnail server fails.
                if isinstance(e, GeneratorExit):
                    raise
                if start + 3 < time.time():
                    # start time is up, something is wrong here
                    raise RuntimeError('unable to connect to thumbnail server')
                yield kaa.delay(0.01)

    def schedule(self, id, filename, imagename, priority):
        if not self.id:
            # Not connected yet, schedule job later
            self._schedules.append((id, filename, imagename, priority))
            return
        # server rpc calls
        self.rpc('schedule', (self.id, id), filename, imagename, priority)

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
            if job.priority != Thumbnail.PRIORITY_LOW:
                self.rpc('set_priority', (self.id, job.id), Thumbnail.PRIORITY_LOW)

_client = Client()
connect = _client.connect
