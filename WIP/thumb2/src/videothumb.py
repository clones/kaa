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
import glob
import os
import stat

# kaa imports
import kaa.notifier
import kaa.imlib2

# kaa.thumb imports
from thumbnailer import epeg, png, failed


class VideoThumb(object):
    """
    Class to handle video thumbnailing.
    """
    def __init__(self, thumbnailer):
        self._jobs = []
        self._current = None

        self._notify_client = thumbnailer._notify_client
        self._create_failed_image = thumbnailer._create_failed_image
        self._debug = thumbnailer._debug

        self.child = kaa.notifier.Process(['mplayer', '-nosound', '-vo', 'png',
                                           '-frames', '8', '-zoom', '-ss' ])
        self.child.signals['completed'].connect(self._completed)
        self.child.signals['stdout'].connect(self._handle_std)
        self.child.signals['stderr'].connect(self._handle_std)


    def append(self, job):
        self._jobs.append(job)
        self._run()


    def _handle_std(self, line):
        self._child_std.append(line)


    def _run(self):
        if self.child.is_alive() or not self._jobs or self._current:
            return True
        self._current = self._jobs.pop(0)

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
                self._create_failed_image(self._current)
                self._notify_client()
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
            self._debug(job.client, self._child_std)
            self._create_failed_image(job)
            self._notify_client(job)
            job = None
            self._run()
            return

        # scale thumbnail
        width, height = job.size
        image = kaa.imlib2.open_without_cache(captures[-1])
        if image.width > width or image.height > height:
            image = image.scale_preserve_aspect((width,height))
        if image.width * 3 > image.height * 4:
            # fix image with blank bars to be 4:3
            nh = (image.width*3)/4
            ni = kaa.imlib2.new((image.width, nh))
            ni.blend(image, (0,(nh- image.height) / 2))
            image = ni
        elif image.width * 3 < image.height * 4:
            # strange aspect, let's guess it's 4:3
            new_size = (image.width, (image.width*3)/4)
            image = image.scale((new_size))

        try:
            png(job.filename, job.imagefile + '.png', job.size, image._image)
            job.imagefile += '.png'
        except (IOError, ValueError):
            self._create_failed_image(job)

        # remove old stuff
        for capture in captures:
            os.remove(capture)

        # notify client and start next video
        self._notify_client(job)
        self._run()
