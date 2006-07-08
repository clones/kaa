# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# videothumb - create a thumbnail for video files
# -----------------------------------------------------------------------------
# $Id$
#
# This file provides a function to create video thumbnails in the
# background.  It will start a mplayer to create the thumbnail. It
# uses the notifier loop to do this without blocking.
#
# Loosly based on videothumb.py commited to the freevo wiki
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
import glob
import os
import stat

# kaa imports
import kaa.notifier
import kaa.imlib2

# kaa.thumb imports
from libthumb import epeg, png, failed


class VideoThumb(object):
    """
    Class to handle video thumbnailing.
    """
    def __init__(self, thumbnailer):
        self.jobs = []
        self._current = None

        self.notify_client = thumbnailer.notify_client
        self.create_failed = thumbnailer.create_failed

        self.child = kaa.notifier.Process(['mplayer', '-nosound', '-vo',
                                           'png:z=2', '-frames', '10',
                                           '-zoom', '-ss' ])
        self.child.signals['completed'].connect(self._completed)
        self.child.signals['stdout'].connect(self._handle_std)
        self.child.signals['stderr'].connect(self._handle_std)


    def append(self, job):
        self.jobs.append(job)
        self._run()


    def _handle_std(self, line):
        self._child_std.append(line)


    def _run(self):
        if self.child.is_alive() or not self.jobs or self._current or \
               kaa.notifier.shutting_down:
            return True
        self._current = self.jobs.pop(0)

        try:
            mminfo = self._current.metadata
            pos = str(int(mminfo.video[0].length / 2.0))
            if hasattr(mminfo, 'type'):
                if mminfo.type in ('MPEG-TS', 'MPEG-PES'):
                    pos = str(int(mminfo.video[0].length / 20.0))
        except:
            # else arbitrary consider that file is 1Mbps and grab position
            # at 10%
            try:
                pos = os.stat(self._current.filename)[stat.ST_SIZE]/1024/1024/10.0
            except (OSError, IOError):
                # send message to client, we are done here
                self.create_failed(self._current)
                self.notify_client()
                return
            if pos < 10:
                pos = '10'
            else:
                pos = str(int(pos))

        self._child_std = []
        self.child.start([pos, self._current.filename])


    def _completed(self, code):
        job = self._current
        self._current = None

        # find thumbnails
        captures = glob.glob('000000??.png')
        if not captures:
            # strange, no image files found
            self.message(self._child_std)
            self.create_failed(job)
            self.notify_client(job)
            job = None
            self._run()
            return

        # find the best image
        current_capture = captures[0], os.stat(captures[0])[stat.ST_SIZE]
        for c in captures[1:]:
            if os.stat(c)[stat.ST_SIZE] > current_capture[1]:
                current_capture = c, os.stat(c)[stat.ST_SIZE]
        current_capture = current_capture[0]
        
        try:
            # scale thumbnail
            width, height = job.size
            image = kaa.imlib2.open_without_cache(current_capture)
            if image.width > width or image.height > height:
                image = image.scale_preserve_aspect((width,height))
            if image.width * 3 > image.height * 4:
                # fix image with blank bars to be 4:3
                nh = (image.width*3)/4
                ni = kaa.imlib2.new((image.width, nh))
                ni.draw_rectangle((0,0), (image.width, nh), (0,0,0,255), True)
                ni.blend(image, dst_pos=(0,(nh- image.height) / 2))
                image = ni
            elif image.width * 3 < image.height * 4:
                # strange aspect, let's guess it's 4:3
                new_size = (image.width, (image.width*3)/4)
                image = image.scale((new_size))

            try:
                png(job.filename, job.imagefile + '.png', job.size,
                    image._image)
                job.imagefile += '.png'
            except (IOError, ValueError):
                self.create_failed(job)

            # remove old stuff
            for capture in captures:
                os.remove(capture)

        except Exception, e:
            self.message('error: %s', e)
        # notify client and start next video
        self.notify_client(job)
        self._run()
