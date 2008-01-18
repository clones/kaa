# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# crawl.py - Crawl filesystem and monitor it
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006-2008 Dirk Meyer
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
import time
import logging

# kaa imports
import kaa
from kaa.inotify import INotify

# kaa.beacon imports
from parser import parse
from config import config
import cpuinfo
import utils
import time

# get logging object
log = logging.getLogger('beacon.crawler')

try:
    WATCH_MASK = INotify.MODIFY | INotify.CLOSE_WRITE | INotify.DELETE | \
                 INotify.CREATE | INotify.DELETE_SELF | INotify.UNMOUNT | \
                 INotify.MOVE
except:
    WATCH_MASK = None


class MonitorList(dict):

    def __init__(self, inotify):
        dict.__init__(self)
        self._inotify = inotify

    def add(self, dirname, use_inotify=True):
        if self._inotify and use_inotify:
            log.debug('add inotify for %s' % dirname)
            try:
                self._inotify.watch(dirname[:-1], WATCH_MASK)
                self[dirname] = True
                return
            except IOError, e:
                log.error(e)
        self[dirname] = False

    def remove(self, dirname, recursive=False):
        if recursive:
            for d in self.keys()[:]:
                if d.startswith(dirname):
                    self.remove(d)
            return
        if self.pop(dirname):
            log.info('remove inotify for %s' % dirname)
            self._inotify.ignore(dirname[:-1])


class Crawler(object):
    """
    Class to crawl through a filesystem and check for changes. If inotify
    support is enabled in the kernel, this class will use it to avoid
    polling the filesystem.
    """
    active = 0
    nextid = 0

    def __init__(self, db, use_inotify=True):
        """
        Init the Crawler.
        Parameter db is a beacon.db.Database object.
        """
        self._db = db
        Crawler.nextid += 1
        self.num = Crawler.nextid

        # set up inotify
        self._inotify = None
        cb = kaa.WeakCallback(self._inotify_event, INotify.MODIFY)
        cb.set_user_args_first(True)
        self._bursthandler = utils.BurstHandler(config.crawler.growscan, cb)
        if use_inotify:
            try:
                self._inotify = INotify()
                self._inotify.signals['event'].connect(self._inotify_event)
            except SystemError, e:
                log.warning('%s', e)

        # create monitoring list with inotify
        self.monitoring = MonitorList(self._inotify)

        # root items that are 'appended'
        self._root_items = []

        # If this env var is non-zero, initialize the update timer to
        # 0 so that we do initial indexing as quickly as possible.  Mainly
        # used for debugging/testing.
        self.parse_timer = config.crawler.scantime
        if os.getenv("BEACON_EAT_CYCLES"):
            log.info('all your cpu are belong to me')
            self.parse_timer = 0

        kaa.main.signals["shutdown"].connect_weak(self.stop)

        # create internal scan variables
        self._scan_list = []
        self._scan_dict = {}
        self._scan_function = None
        self._scan_restart_timer = None
        self._crawl_start_time = None
        self._startup = True


    def append(self, item):
        """
        Append a directory to be crawled and monitored.
        """
        log.info('crawl %s', item)
        self._root_items.append(item)
        self._scan_add(item, True)


    def stop(self):
        """
        Stop the crawler and remove the inotify watching.
        """
        kaa.main.signals["shutdown"].disconnect(self.stop)
        # stop running scan process
        self._scan_list = []
        self._scan_dict = []
        if self._scan_function:
            self._scan_function.stop()
            self._scan_function = None
            self._scan_stop([], False)
        # stop inotify
        self._inotify = None
        # stop restart timer
        if self._scan_restart_timer:
            self._scan_restart_timer.stop()
            self._scan_restart_timer = None


    def __repr__(self):
        return '<kaa.beacon.Crawler>'


    # -------------------------------------------------------------------------
    # Internal functions - INotify
    # -------------------------------------------------------------------------

    def _inotify_event(self, mask, name, *args):
        """
        Callback for inotify.
        """
        if mask & INotify.MODIFY and self._bursthandler.is_growing(name):
            # A file was modified. Do this check as fast as we can because the
            # events may come in bursts when a file is just copied. In this case
            # a timer is already active and we can return. It still uses too
            # much CPU time in the burst, but there is nothing we can do about
            # it.
            return True

        if self._db.read_lock.is_locked():
            # The database is locked now and we may want to change entries.
            # FIXME: make sure the inotify events still stay in the same order
            con = self._db.read_lock.signals['unlock'].connect_once
            con(self._inotify_event, mask, name, *args)
            return True

        # some debugging to find a bug in beacon
        log.info('inotify: event %s for "%s"', mask, name)

        item = self._db.query_filename(name)
        if not item._beacon_parent.filename in self.monitoring:
            # that is a different monitor, ignore it
            # FIXME: this is a bug (missing feature) in inotify
            return True

        if item._beacon_name.startswith('.'):
            # hidden file, ignore except in move operations
            if mask & INotify.MOVE and args:
                # we moved from a hidden file to a good one. So handle
                # this as a create for the new one.
                log.info('inotify: handle move as create for %s', args[0])
                self._inotify_event(INotify.CREATE, args[0])
            return True

        # ---------------------------------------------------------------------
        # MOVE_FROM -> MOVE_TO
        # ---------------------------------------------------------------------

        if mask & INotify.MOVE and args and item._beacon_id:
            # Move information with source and destination
            move = self._db.query_filename(args[0])
            if move._beacon_name.startswith('.'):
                # move to hidden file, delete
                log.info('inotify: move to hidden file, delete')
                self._inotify_event(INotify.DELETE, name)
                return True

            if move._beacon_id:
                # New item already in the db, delete it first
                log.info('inotify delete: %s', item)
                self._db.delete_object(move)
            changes = {}
            if item._beacon_parent._beacon_id != move._beacon_parent._beacon_id:
                # Different directory, set new parent
                changes['parent'] = move._beacon_parent._beacon_id
            if item._beacon_data['name'] != move._beacon_data['name']:
                # New name, set name to item
                move._beacon_data = dict(move._beacon_data)
                if move._beacon_data.get('image') == move._beacon_data['name']:
                    # update image to new filename
                    changes['image'] = move._beacon_data['name']
                changes['name'] = move._beacon_data['name']
            if changes:
                log.info('inotify: move: %s', changes)
                self._db.update_object(item._beacon_id, **changes)

            # Now both directories need to be checked again
            self._scan_add(item._beacon_parent, recursive=False)
            self._scan_add(move._beacon_parent, recursive=False)

            if not mask & INotify.ISDIR:
                # commit changes so that the client may get notified
                self._db.commit()
                return True

            # The directory is a dir. We now remove all the monitors to that
            # directory and crawl it again. This keeps track for softlinks that
            # may be different or broken now.
            self.monitoring.remove(name + '/', recursive=True)
            # now make sure the directory is parsed recursive again
            self._scan_add(move, recursive=True)
            # commit changes so that the client may get notified
            self._db.commit()
            return True

        # ---------------------------------------------------------------------
        # MOVE_TO, CREATE, MODIFY or CLOSE_WRITE
        # ---------------------------------------------------------------------

        if mask & INotify.MOVE and args:
            # We have a move with to and from, but the from item is not in
            # the db. So we handle it as a simple MOVE_TO
            name = args[0]

        if os.path.exists(name):
            # The file exists. So it is either created or modified, we don't
            # care right now.
            if item._beacon_isdir:
                # It is a directory. Just do a full directory rescan.
                recursive = not (mask & INotify.MODIFY)
                self._scan_add(item, recursive=recursive)
                if name.lower().endswith('/video_ts'):
                    # it could be a dvd on hd
                    self._scan_add(item._beacon_parent, recursive=False)
                return True

            # handle bursts of inotify events when a file is growing very
            # fast (e.g. cp)
            if mask & INotify.CLOSE_WRITE:
                self._bursthandler.remove(name)

            # parent directory changed, too. Even for a simple modify of an
            # item another item may be affected (xml metadata, images)
            # so scan the file by rechecking the parent dir
            self._scan_add(item._beacon_parent, recursive=False)
            return True

        # ---------------------------------------------------------------------
        # DELETE
        # ---------------------------------------------------------------------

        # before we delete, maybe the filesystem was just umounted
        if mask & INotify.UNMOUNT:
            # Oops, our filesystem was umounted. This should never happen
            # since all removable drives which could be umounted are on
            # a different media in beacon. It happens sometimes on system
            # shutdown, so we just ignore this event for now.
            if name + '/' in self.monitoring:
                self.monitoring.remove(name + '/', recursive=True)
            return True

        # The file does not exist, we need to delete it in the database
        log.info('inotify: delete %s', item)
        self._db.delete_object(item)

        # remove directory and all subdirs from the inotify. The directory
        # is gone, so all subdirs are invalid, too.
        if name + '/' in self.monitoring:
            # FIXME: This is not correct when you deal with softlinks.
            # If you move a directory with relative softlinks, the new
            # directory to monitor is different.
            self.monitoring.remove(name + '/', recursive=True)
        # rescan parent directory
        self._scan_add(item._beacon_parent, recursive=False)
        # commit changes so that the client may get notified
        self._db.commit()
        return True


    # -------------------------------------------------------------------------
    # Internal functions - Scanner
    # -------------------------------------------------------------------------

    def _scan_add(self, directory, recursive):
        """
        Add a directory to the list of directories to scan.
        """
        if directory.filename in self._scan_dict:
            # ok then, already in list and close to the beginning
            # if we are called bu inotify (because it has to be scanned
            # once) or somewhere else in normal mode. In both cases we
            # don't do anything.
            return False

        if not recursive:
            # called from inotify. this means the file can not be in
            # the list as recursive only again from inotify. Add to the
            # beginning of the list, it is important and fast.
            self._scan_list.insert(0, (directory, False))
        else:
            # called from inside the crawler recursive or by massive changes
            # from inotify. In both cases, add to the end of the list because
            # this takes much time.
            if directory.filename in self.monitoring:
                # already scanned
                # TODO: softlink dirs are not handled correctly, they may be
                # scanned twiece.
                return False
            self._scan_list.append((directory, recursive))
        self._scan_dict[directory.filename] = directory

        # start ._scan_function
        if self._scan_function == None:
            Crawler.active += 1
            self._scan_function = kaa.OneShotTimer(self._scan_start)
            self._scan_function.start(0)


    def _scan_start(self):
        """
        Start the scan function using YieldFunction.
        """
        if self._crawl_start_time is None:
            self._crawl_start_time = time.time()

        interval = self.parse_timer * Crawler.active
        if (cpuinfo.cpuinfo()[cpuinfo.IDLE] < 40 or \
            cpuinfo.cpuinfo()[cpuinfo.IOWAIT] > 20) and interval < 1:
            # too much CPU load, slow down
            interval *= 2
        if (cpuinfo.cpuinfo()[cpuinfo.IDLE] < 80 or \
            cpuinfo.cpuinfo()[cpuinfo.IOWAIT] > 40) and interval < 1:
            # way too much CPU load, slow down even more
            interval *= 2
        self._scan_function = kaa.YieldFunction(self._scan, interval)
        directory, recursive = self._scan_list.pop(0)
        del self._scan_dict[directory.filename]
        self._scan_function(directory)
        self._scan_function.connect(self._scan_stop, recursive)


    def _scan_stop(self, subdirs, recursive):
        """
        The scan function finished.
        """
        if recursive:
            # add results to the list of files to scan
            for d in subdirs:
                self._scan_add(d, True)
        if self._scan_list:
            # start again
            self._scan_start()
            return
        # crawler finished
        self._scan_function = None
        self._startup = False
        log.info('crawler %s finished; took %0.1f seconds.', \
                 self.num, time.time() - self._crawl_start_time)
        self._crawl_start_time = None
        Crawler.active -= 1

        # commit changes so that the client may get notified
        self._db.commit()

        if not self._inotify:
            # Inotify is not in use. This means we have to start crawling
            # the filesystem again in 10 seconds using the restart function.
            # The restart function will crawl with a much higher intervall to
            # keep the load on the system down.
            log.info('schedule rescan')
            self._scan_restart_timer = kaa.WeakOneShotTimer(self._scan_restart)
            self._scan_restart_timer.start(10)


    def _scan_restart(self):
        """
        Restart the crawler when inotify is not enabled.
        """
        # set parser time to one second to keep load down
        self.parse_timer = 1

        # reset self.monitoring and add all directories once passed to
        # this object with 'append' again.
        self.monitoring = MonitorList(self._inotify)
        for item in self._root_items:
            self._scan_add(item, recursive=True)


    def _scan(self, directory):
        """
        Scan a directory and all files in it, return list of subdirs.
        """
        log.info('scan directory %s', directory.filename)

        if not os.path.exists(directory.filename):
            log.info('unable to scan %s', directory.filename)
            yield []

        if directory._beacon_parent and \
               not directory._beacon_parent._beacon_isdir:
            log.warning('parent of %s is no directory item', directory)
            if hasattr(directory, 'filename') and \
                   directory.filename + '/' in self.monitoring:
                self.monitoring.remove(directory.filename + '/', recursive=True)
            yield []

        # parse directory
        async = parse(self._db, directory, check_image=self._startup)
        if isinstance(async, kaa.InProgress):
            yield async

        # check if it is still a directory
        if not directory._beacon_isdir:
            log.warning('%s is no directory item', directory)
            if hasattr(directory, 'filename') and \
                   directory.filename + '/' in self.monitoring:
                self.monitoring.remove(directory.filename + '/', recursive=True)
            yield []

        if directory._beacon_islink:
            # it is a softlink. Add directory with inotify to the monitor
            # list and with inotify using the realpath (later)
            self.monitoring.add(directory.filename, use_inotify=False)
            dirname = os.path.realpath(directory.filename)
            directory = self._db.query_filename(dirname)
            async = parse(self._db, directory, check_image=self._startup)
            if isinstance(async, kaa.InProgress):
                yield async

        # add to monitor list using inotify
        self.monitoring.add(directory.filename)

        # iterate through the files
        subdirs = []
        counter = 0

        result = self._db.query(parent=directory)
        if isinstance(result, kaa.InProgress):
            yield result
            result = result()
        for child in result:
            if child._beacon_isdir:
                # add directory to list of files to return
                subdirs.append(child)
                continue
            # check file
            async = parse(self._db, child, check_image=self._startup)
            if isinstance(async, kaa.InProgress):
                yield async
                async = async()
            counter += async * 20
            while counter >= 20:
                counter -= 20
                yield kaa.YieldContinue
                if cpuinfo.cpuinfo()[cpuinfo.IDLE] < 50 or \
                       cpuinfo.cpuinfo()[cpuinfo.IOWAIT] > 30:
                    yield kaa.YieldContinue
            counter += 1

        if not subdirs:
            # No subdirectories that need to be checked. Add some extra
            # attributes based on the found items (recursive back to parents)
            result = self._add_directory_attributes(directory)
            if isinstance(result, kaa.InProgress):
                yield result
        yield subdirs


    @kaa.yield_execution()
    def _add_directory_attributes(self, directory):
        """
        Add some extra attributes for a directory recursive. This function
        checkes album, artist, image and length. When there are changes,
        go up to the parent and check it, too.
        """
        data = { 'length': 0, 'artist': u'', 'album': u'', 'image': '' }
        check_attr = data.keys()[:]
        check_attr.remove('length')

        result = self._db.query(parent=directory)
        if isinstance(result, kaa.InProgress):
            yield result
            result = result()
        for child in result:
            data['length'] += child._beacon_data.get('length', 0) or 0
            for attr in check_attr:
                value = child._beacon_data.get(attr, data[attr])
                if data[attr] == '':
                    data[attr] = value
                if data[attr] != value:
                    data[attr] = None
                    check_attr.remove(attr)

        if data['image'] and not (data['artist'] or data['album']):
            # We have neither artist nor album. So this seems to be a video
            # or an image directory and we don't want to set the image from
            # maybe one item in that directory as our directory image.
            data['image'] = None

        if not directory._beacon_data['image_from_items'] and \
               directory._beacon_data['image']:
            # The directory had an image defined and found by the parser.
            # Delete image from data, we don't want to override it.
            del data['image']

        for attr in data.keys():
            if not data[attr]:
                # Set empty string to None
                data[attr] = None
        for attr in data.keys():
            if data[attr] != directory._beacon_data[attr]:
                break
        else:
            # no changes.
            yield True

        if 'image' in data:
            # Mark that this image was taken based on this function, later
            # scans can remove it if it differs.
            data['image_from_items'] = True

        while self._db.read_lock.is_locked():
            yield self._db.read_lock.yield_unlock()

        # update directory in database
        self._db.update_object(directory._beacon_id, **data)
        directory._beacon_data.update(data)

        # check parent
        if directory._beacon_parent.filename in self.monitoring:
            result = self._add_directory_attributes(directory._beacon_parent)
            if isinstance(result, kaa.InProgress):
                yield result
