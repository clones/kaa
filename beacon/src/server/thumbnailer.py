# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# thumbnailer.py - Server interface for the thumbnailer
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006-2009 Dirk Meyer
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

# python imports
import os
import sys
import logging
import urllib
import time
import stat

# kaa imports
import kaa
import kaa.metadata
import kaa.imlib2
import kaa.rpc

# kaa.beacon imports
from .. import libthumb
from videothumb import VideoThumb
from config import config
import scheduler

# get logging object
log = logging.getLogger('beacon.thumbnail')

DOWNLOAD_THREAD = 'beacon.download'


@kaa.threaded(DOWNLOAD_THREAD)
def download(url, filename):
    """
    Download url and store in filename
    """
    if os.path.exists(filename):
        return None
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    log.info('fetch %s', url)
    image = urllib.urlopen(url).read()
    open(filename, 'w').write(image)


class Job(object):
    """
    A job with thumbnail information.
    """
    def __init__(self, id, filename, imagefile, url, priority):
        self.client, self.id = id
        self.filename = filename
        # imagefile has %s for normal/large and not ext
        self.imagefile = imagefile
        self.url = url
        self.priority = priority
        self._cmdid = imagefile


    def __cmp__(self, other):
        if not isinstance(other, Job):
            return 1
        return self._cmdid != other._cmdid


class Thumbnailer(object):
    """
    Main thumbnailer class.
    """
    def __init__(self, tmpdir, config_dir, scheduler=None):
        self.next_client_id = 0
        self.clients = []
        self.jobs = []
        self._delayed_jobs = {}
        self._timer = kaa.OneShotTimer(self.step)
        self._ipc = kaa.rpc.Server(os.path.join(tmpdir, 'socket'))
        self._ipc.signals['client-connected'].connect(self.client_connect)
        self._ipc.register(self)

        # Load configuration for scheduler settings.
        config.load(os.path.join(config_dir, 'config'))
        config.watch()
        if scheduler:
            config.autosave = False
            config.scheduler.policy = scheduler

        # video module
        self.videothumb = VideoThumb(self, config)

    # -------------------------------------------------------------------------
    # Client handling
    # -------------------------------------------------------------------------

    def client_connect(self, client):
        """
        Connect a new client to the server.
        """
        client.signals['closed'].connect(self.client_disconnect, client)
        self.next_client_id += 1
        self.clients.append((self.next_client_id, client))
        client.rpc('connect', self.next_client_id)


    def client_disconnect(self, client):
        """
        IPC callback when a client is lost.
        """
        for client_info in self.clients[:]:
            id, c = client_info
            if c == client:
                for j in self.jobs[:]:
                    if j.client == id:
                        self.jobs.remove(j)
                for j in self.videothumb.jobs[:]:
                    if j.client == id:
                        self.videothumb.jobs.remove(j)
                if client_info == self.clients[0]:
                    # the main beacon process stopped
                    sys.exit(0)
                self.clients.remove(client_info)
                return


    # -------------------------------------------------------------------------
    # Internal API
    # -------------------------------------------------------------------------

    def notify_client(self, job, search=True):
        for id, client in self.clients:
            if id == job.client:
                client.rpc('finished', job.id, job.filename, job.imagefile)
                break
        if not search:
            return
        for j in [ j for j in self.jobs[:] if j == job ]:
            self.notify_client(j, False)
            self.jobs.remove(j)
        for j in [ j for j in self.videothumb.jobs[:] if j == job ]:
            self.notify_client(j, False)
            self.videothumb.jobs.remove(j)


    def create_failed(self, job):
        job.imagefile = job.imagefile % '/fail/beacon/'
        if not os.path.isdir(os.path.dirname(job.imagefile)):
            os.makedirs(os.path.dirname(job.imagefile), 0700)
        libthumb.failed(job.filename, job.imagefile)
        return


    @kaa.coroutine()
    def download(self, job):
        if not os.path.isdir(os.path.dirname(job.filename)):
            os.makedirs(os.path.dirname(job.filename))
        try:
            yield download(job.url, job.filename)
            metadata = kaa.metadata.parse(job.filename)
            if not metadata or metadata['media'] != kaa.metadata.MEDIA_IMAGE:
                raise IOError('%s is no image' % job.url)
        except Exception, e:
            log.error('unable to download image: %s', str(e))
            if os.path.isfile(job.filename):
                os.unlink(job.filename)
            # FIXME: handle failed download
            yield False
        self.jobs.append(job)
        self.jobs.sort(lambda x,y: cmp(x.priority, y.priority))
        self.schedule_next()


    def step(self):
        """
        Process one job
        """
        if not self.jobs or kaa.main.is_shutting_down():
            return False

        job = self.jobs.pop(0)

        if job.url and not os.path.isfile(job.filename):
            # we need to download first
            self.download(job)
            self.schedule_next(fast=True)
            return True

        for size in ('large', 'normal'):
            # iterate over the sizes
            imagefile = job.imagefile % size
            if not os.path.isfile(imagefile):
                break
            metadata = kaa.metadata.parse(imagefile)
            if not metadata:
                break
            mtime = metadata.get('Thumb::MTime')
            if not mtime or mtime != str(os.stat(job.filename)[stat.ST_MTIME]):
                # needs an update
                break
        else:
            # we did not break out of the loop, this means we have both thumbnails
            # and the mtime is also correct. Refuse the recreate thumbnail
            self.notify_client(job)
            self.schedule_next(fast=True)
            return True
        if job.filename.lower().endswith('jpg'):
            # try epeg for fast thumbnailing
            try:
                if os.stat(job.filename)[stat.ST_SIZE] < 1024*1024:
                    raise ValueError('no photo, use imlib2')
                libthumb.epeg(job.filename, job.imagefile % 'large', (256, 256))
                libthumb.epeg(job.filename, job.imagefile % 'normal', (128, 128))
                self.notify_client(job)
                self.schedule_next()
                return True
            except (IOError, ValueError):
                pass
        try:
            # try normal imlib2 thumbnailing
            libthumb.png(job.filename, job.imagefile % 'large', (256, 256))
            libthumb.png(job.filename, job.imagefile % 'normal', (128, 128))
            self.notify_client(job)
            self.schedule_next()
            return True
        except (IOError, ValueError), e:
            pass

        # maybe this is no image
        metadata = kaa.metadata.parse(job.filename)
        if metadata and (metadata['media'] == kaa.metadata.MEDIA_AV or metadata.type == u'DVD'):
            # video file
            job.metadata = metadata
            self.videothumb.queue(job)
            self.schedule_next()
            return True

        # maybe the image is gone now
        if not os.path.exists(job.filename):
            # ignore it in this case
            log.info('no file %s', job.filename)
            self.notify_client(job)
            self.schedule_next()
            return True

        # broken file
        log.info('unable to create thumbnail for %s', job.filename)
        self.create_failed(job)
        self.notify_client(job)
        self.schedule_next()
        return True


    def schedule_next(self, fast=False):
        """
        Schedule next thumbnail based on priority.
        """
        if self._timer.active() or not self.jobs:
            return

        if fast:
            # We already waited the last delay, but didn't end up consuming
            # CPU, so consider our debt paid.
            delay = 0
        else:
            delay = scheduler.next(config.scheduler.policy) * config.scheduler.multiplier

        if self.jobs[0].priority:
            # Thumbnail is high priority, use less of a delay.
            delay /= 10.0

        self._timer.start(delay)


    # -------------------------------------------------------------------------
    # External RPC API
    # -------------------------------------------------------------------------

    @kaa.rpc.expose()
    def schedule(self, id, filename, imagefile, url, priority):
        # FIXME: check if job is already scheduled!!!!
        job = Job(id, filename, imagefile, url, priority)
        self.jobs.append(job)
        self.jobs.sort(lambda x,y: cmp(x.priority, y.priority))
        self.schedule_next()


    @kaa.rpc.expose()
    def set_priority(self, id, priority):
        for schedule in self.jobs, self.videothumb.jobs:
            for job in schedule:
                if id != (job.client, job.id):
                    continue
                job.priority = priority
                schedule.sort(lambda x,y: cmp(x.priority, y.priority))
                return


def create(config_dir, scheduler=None):
    """
    Create thumbnail Unix socket and object
    """
    # create tmp dir and change directory to it
    tmpdir = kaa.tempfile('thumb')
    if not os.path.isdir(tmpdir):
        os.mkdir(tmpdir)
    os.chdir(tmpdir)
    try:
        return Thumbnailer(tmpdir, config_dir, scheduler=None)
    except IOError, e:
        log.error('thumbnail: %s' % e)
        time.sleep(0.1)
        sys.exit(0)
