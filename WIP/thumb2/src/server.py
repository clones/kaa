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

# python imports
import os
import sys
import logging

# insert kaa path information
__site__ = '../lib/python%s.%s/site-packages' % sys.version_info[:2]
__site__ = os.path.normpath(os.path.join(os.path.dirname(__file__), __site__))
if not __site__ in sys.path:
    sys.path.insert(0, __site__)

# kaa imports
from kaa import ipc
import kaa.notifier
import kaa.metadata
import kaa.imlib2

# kaa.thumb imports
from thumbnailer import epeg, png, failed
from videothumb import VideoThumb


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
        self._ipc = ipc.IPCServer(os.path.join(tmpdir, 'socket'))
        self._ipc.register_object(self, 'thumb')
        self._ipc.signals["client_closed"].connect(self._client_closed)

        # video module
        self.videothumb = VideoThumb(self)


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


    def connect(self, callback):
        self.next_client_id += 1
        self.clients.append((self.next_client_id, callback))
        return self.next_client_id


    def schedule(self, id, filename, imagefile, size):

        self._jobs.append(Job(id, filename, imagefile, size))
        if not self._timer.active():
            self._timer.start(0.001)


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
            
    def _client_closed(self, client):
        for client_info in self.clients[:]:
            id, c = client_info
            if ipc.get_ipc_from_proxy(c) == client:
                for j in self._jobs[:]:
                    if j.client == id:
                        self._jobs.remove(j)
                for j in self.videothumb._jobs[:]:
                    if j.client == id:
                        self.videothumb._jobs.remove(j)
                self.clients.remove(client_info)
                return


if __name__ == "__main__":

    shutdown_timer = 5

    @kaa.notifier.execute_in_timer(kaa.notifier.Timer, 1)
    def autoshutdown(server):
        global shutdown_timer
        if len(server.clients) > 0:
            shutdown_timer = 5
            return True
        shutdown_timer -= 1
        if shutdown_timer == 0:
            sys.exit(0)
        return True
    
    try:
        # detach for parent using a new sesion
        os.setsid()
    except OSError:
        # looks like we are started from the shell
        # TODO: start some extra debug here and disable autoshutdown
        pass
    
    # create tmp dir and change directory to it
    tmpdir = os.path.join(kaa.TEMP, 'thumb')
    if not os.path.isdir(tmpdir):
        os.mkdir(tmpdir)
    os.chdir(tmpdir)

    # Setup logger. This module should produce no output at all, but a crash
    # will result in a backtrace which is nice to have.
    handler = logging.FileHandler('log')
    handler.setFormatter(logging.Formatter('%(filename)s %(lineno)s: %(message)s'))
    logging.getLogger().addHandler(handler)

    # create thumbnailer object
    thumbnailer = Thumbnailer(tmpdir)

    # start autoshutdown
    autoshutdown(thumbnailer)

    # loop
    kaa.notifier.loop()
