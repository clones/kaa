# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# server.py - Server interface for the thumbnailer
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

# python imports
import os
import sys
import logging
import time

# kaa imports
import kaa.notifier
import kaa.metadata
import kaa.imlib2
import kaa.rpc

# kaa.thumb imports
from libthumb import epeg, png, failed
from video import VideoThumb

# get logging object
log = logging.getLogger('beacon.thumbnail')

class Job(object):
    """
    A job with thumbnail information.
    """
    def __init__(self, id, filename, imagefile, size):
        self.client, self.id = id
        self.filename = filename
        self.imagefile = imagefile
        self.size = size


class Thumbnailer(object):
    """
    Main thumbnailer class.
    """
    def __init__(self, tmpdir):
        self.next_client_id = 0
        self.clients = []
        self._jobs = []
        self._timer = kaa.notifier.Timer(self._run)
        self._ipc = kaa.rpc.Server(os.path.join(tmpdir, 'socket'))
        self._ipc.signals['client_connected'].connect(self.client_connect)
        self._ipc.connect(self)
        
        # video module
        self.videothumb = VideoThumb(self)


    def client_connect(self, client):
        """
        Connect a new client to the server.
        """
        client.signals['closed'].connect(self.client_disconnect, client)
        self.next_client_id += 1
        self.clients.append((self.next_client_id, client))
        client.rpc('connect')(self.next_client_id)


    def client_disconnect(self, client):
        """
        IPC callback when a client is lost.
        """
        for client_info in self.clients[:]:
            id, c = client_info
            if c == client:
                for j in self._jobs[:]:
                    if j.client == id:
                        self._jobs.remove(j)
                for j in self.videothumb._jobs[:]:
                    if j.client == id:
                        self.videothumb._jobs.remove(j)
                self.clients.remove(client_info)
                return


        
    def _debug(self, client, messages):
        for id, callback in self.clients:
            if id == client:
                callback(0, messages, __ipc_oneway=True, __ipc_noproxy_args=True)
                return


    def _notify_client(self, job):
        for id, callback in self.clients:
            if id == job.client:
                callback(job.id, job.filename, job.imagefile,
                         __ipc_oneway=True, __ipc_noproxy_args=True)
                return


    def _create_failed_image(self, job):
        dirname = os.path.dirname(os.path.dirname(job.imagefile)) + '/fail/kaa/'
        job.imagefile = dirname + os.path.basename(job.imagefile) + '.png'
        if not os.path.isdir(dirname):
            os.makedirs(dirname, 0700)
        failed(job.filename, job.imagefile)
        return


    def _run(self):
        if not self._jobs:
            return False

        job = self._jobs.pop(0)

        # FIXME: check if there is already a file and it is up to date

        if job.filename.lower().endswith('jpg'):
            try:
                epeg(job.filename, job.imagefile + '.jpg', job.size)
                job.imagefile += '.jpg'
                self._notify_client(job)
                return True
            except (IOError, ValueError):
                pass

        try:
            png(job.filename, job.imagefile + '.png', job.size)
            job.imagefile += '.png'
            self._notify_client(job)
            return True
        except (IOError, ValueError), e:
            print e
            pass

        # maybe this is no image
        metadata = kaa.metadata.parse(job.filename)
        if metadata and metadata['media'] == 'video':
            # video file
            job.metadata = metadata
            self.videothumb.append(job)
            return True

        if metadata and metadata['raw_image']:
            try:
                image = kaa.imlib2.open_from_memory(metadata['raw_image'])
                png(job.filename, job.imagefile, job.size, image._image)
            except (IOError, ValueError):
                # raw image is broken
                self._debug(job.client, ['bad image in %s' % job.filename])
                self._create_failed_image(job)
            self._notify_client(job)
            return True

        # broken file
        self._debug(job.client, ['unable to create thumbnail for %s' % job.filename])
        self._create_failed_image(job)
        self._notify_client(job)
        return True


    @kaa.rpc.expose('schedule')
    def schedule(self, id, filename, imagefile, size):

        self._jobs.append(Job(id, filename, imagefile, size))
        if not self._timer.active():
            self._timer.start(0.001)


    @kaa.rpc.expose('remove')
    def remove(self, id):
        for job in self._jobs:
            if id == (job.client, job.id):
                print 'remove job'
                self._jobs.remove(job)
                return
        for job in self.videothumb._jobs:
            if id == (job.client, job.id):
                print 'remove video job'
                self.videothumb._jobs.remove(job)
                return

    @kaa.rpc.expose('shutdown')
    def shutdown(self):
        sys.exit(0)

        
def loop():
    # create tmp dir and change directory to it
    tmpdir = os.path.join(kaa.TEMP, 'thumb')
    if not os.path.isdir(tmpdir):
        os.mkdir(tmpdir)
    os.chdir(tmpdir)

    # create thumbnailer object
    try:
        thumbnailer = Thumbnailer(tmpdir)
    except IOError, e:
        log.error('thumbnail: %s' % e)
        time.sleep(0.1)
        sys.exit(0)

    # set nice level
    os.nice(19)
    
    # loop
    kaa.notifier.loop()
    log.info('stop thumbnail server')
    sys.exit(0)
