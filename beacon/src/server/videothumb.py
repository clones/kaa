# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# videothumb - create a thumbnail for video files
# -----------------------------------------------------------------------------
# $Id$
#
# This file provides a function to create video thumbnails in the
# background.  It will start a mplayer to create the thumbnail. It
# uses the generic mainloop to do this without blocking.
#
# Loosly based on videothumb.py commited to the freevo wiki
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
import glob
import os
import stat
import logging
import random
import re

# kaa imports
import kaa
import kaa.metadata
import kaa.imlib2

# kaa.beacon imports
from .. import libthumb
import scheduler

# get logging object
log = logging.getLogger('beacon.thumbnail')


class VideoThumb(object):
    """
    Class to handle video thumbnailing.
    """
    def __init__(self, thumbnailer, config):
        self.notify_client = thumbnailer.notify_client
        self.create_failed = thumbnailer.create_failed

        # Determine the best supported schedtool policy for this OS.
        policies = os.popen('schedtool -r').read()
        for policy, switch in ('IDLEPRIO', '-D'), ('BATCH', '-B'):
            if re.search(r'SCHED_%s.*prio' % policy, policies):
                sched = ['schedtool', switch, '-e']
                break
        else:
            # Schedtool not available; fallback to nice.
            sched = ['nice']

        # Config object passed from Thumbnailer instance.
        self.config = config
        self.mplayer = kaa.Process2(sched + ['mplayer', '-nosound', '-vo', 'png:z=2', '-benchmark', '-quiet',
                                     '-frames', '10', '-osdlevel', '0', '-nocache', '-zoom', '-ss' ])
        # Dummy read handler, consuming mplayer's stdout/stderr so that flow control
        # doesn't block us.
        self.mplayer.signals['read'].connect(lambda data: None)

        self.jobs = []
        # The CoroutineInProgress for thumbnailer coroutine.
        self._ip = None


    def queue(self, job):
        """
        Add a new video thumbnail job
        """
        self.jobs.append(job)
        if not self._ip or self._ip.finished:
            # Thumbnailer coroutine is not running, start it now.
            self._ip = self._thumbnailer()

    
    @kaa.coroutine()
    def _thumbnailer(self):
        while self.jobs and not kaa.main.is_stopped():
            job = self.jobs.pop(0)
            log.info('Now processing video thumbnail job: file=%s, qlen=%d', job.filename, len(self.jobs))

            for size in ('large', 'normal'):
                imagefile = job.imagefile % size
                if not os.path.isfile(imagefile):
                    # One (or both) of the large and normal thumbnails don't exist, so
                    # we must generate.
                    break
                metadata = kaa.metadata.parse(imagefile)
                mtime = metadata.get('Thumb::MTime')
                if mtime != str(os.stat(job.filename)[stat.ST_MTIME]):
                    # File mtime doesn't match the stored mtime in the thumbnail metadata,
                    # so must regenerate.
                    break
            else:
                # No thumb generation needed.
                continue

            # XXX: this isn't very effective because we can't throttle mplayer
            # once it's running.  We run mplayer at the lowest possible priority
            # (if schedtool is available), so that'll have to suffice.
            # IDEA: actually we can throttle mplayer, if we remove -benchmark and pass -fps.
            delay = scheduler.next(self.config.scheduler.policy) * self.config.scheduler.multiplier
            if delay:
                # too much CPU load, slow down
                yield kaa.delay(delay)

            try:
                success = yield self._generate(job)
            except Exception:
                success = False

            if not success:
                # Something went awry, generate a failed thumbnail file.
                self.create_failed(job)

            # Notify client via rpc that this thumbnail job is done.
            self.notify_client(job)


    @kaa.coroutine()
    def _generate(self, job):
        """
        Generates the thumbnail by spawning MPlayer.

        Yields True if generation was successful, and False otherwise.
        """
        mpargs = [job.filename]
        pos = 0
        try:
            length = job.metadata.length
            if job.metadata.type == u'DVD':
                # Find longest title.
                longest = sorted(job.metadata.tracks, key = lambda t: t.length)[-1]
                # Small heuristic: favor lowest title that's at least 80% of the longest title.
                track = min([t for t in job.metadata.tracks if t.length > longest.length * 0.8])
                length = track.length
                mpargs[0] = 'dvd://%d' % track.trackno
                mpargs.extend(['-dvd-device', job.filename])
            elif job.metadata.video[0].length:
                length = job.metadata.video[0].length

            # Pick a random position between 30-70%.  By randomizing, we give
            # the user the option to delete the original thumbnail and regenerate
            # a (likely) new one, in case the previous one wasn't very representative.
            pos = length * random.randrange(30, 70) / 100.0
            if hasattr(job.metadata, 'type'):
                # FIXME: dischi, this logic needs a comment.
                if job.metadata.type in ('MPEG-TS', 'MPEG-PES'):
                    pos = length / 20.0
        except (AttributeError, IndexError, TypeError):
            # else arbitrary consider that file is 1Mbps and grab position at 10%
            try:
                pos = os.stat(job.filename)[stat.ST_SIZE]/1024/1024/10.0
            except (OSError, IOError):
                yield False

            if pos < 10:
                # FIXME: needs another comment; is this because keyframes tend to be
                # every 10 seconds?  But if length < 10, won't we risk seeking to EOF and
                # not getting any thumbnail at all?"
                pos = 10

        # Give MPlayer 10 seconds to generate the thumbnail before we give up
        # and kill it.  Some video files cause mplayer to runaway.
        self.mplayer.start([str(pos)] + mpargs).timeout(10, abort=True)

        # Yield the 'finished' signal rather than self.mplayer, because the Process's
        # IP might finish due to timeout, but we don't want to proceed until the
        # child is dead.  (If it does timeout, the Process InProgress will be aborted,
        # which causes the child to get killed.)
        yield kaa.inprogress(self.mplayer.signals['finished'])
        
        # MPlayer is done, look for the screenshots it created.
        captures = glob.glob('000000??.png')
        if not captures:
            # No images, Mplayer crashed on this file?
            yield False

        # find the largest image (making assumption it's the best)
        current_capture = sorted(captures, key=lambda x: os.stat(x)[stat.ST_SIZE])[-1]
        try:
            # scale thumbnail
            for size, width, height in (('large', 256, 256), ('normal', 128, 128)):
                image = kaa.imlib2.open_without_cache(current_capture)
                # FIXME: Thumb::Mimetype ends up being wrong.
                libthumb.png(job.filename, job.imagefile % size, (width, height), image._image)

            # remove old files.
            [ os.remove(fname) for fname in captures ]
        except Exception, e:
            log.exception('Thumbnailing of MPlayer screenshots failed')
            yield False

        yield True
