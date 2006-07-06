# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# crawl.py - Crawl filesystem and monitor it
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-beacon - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
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
from kaa.notifier import Timer, OneShotTimer

# kaa.beacon imports
from parser import parse
from inotify import INotify
from directory import Directory

# get logging object
log = logging.getLogger('beacon.crawler')

try:
    WATCH_MASK = INotify.MODIFY | INotify.CLOSE_WRITE | INotify.DELETE | \
                 INotify.CREATE | INotify.DELETE_SELF | INotify.UNMOUNT | \
                 INotify.MOVE
except:
    WATCH_MASK = None

# timer for growing files (cp, download)
GROWING_TIMER = 5


class Crawler(object):
    """
    Class to crawl through a filesystem and check for changes. If inotify
    support is enabled in the kernel, this class will use it to avoid
    polling the filesystem.
    """
    PARSE_TIMER  = 0.02
    UPDATE_TIMER = 0.03

    active = 0
    nextid = 0
    
    def __init__(self, db, use_inotify=True):
        """
        Init the Crawler.
        Parameter db is a beacon.db.Database object.
        The Crawler is used by Mountpoint
        """
        self.db = db
        self.monitoring = []
        self.scan_directory_items = []
        self.check_mtime_items = []
        self.update_items = []
        Crawler.nextid += 1
        self.num = Crawler.nextid
        if use_inotify:
            try:
                self.inotify = INotify()
                self.inotify.signals['event'].connect(self.inotify_callback)
            except SystemError, e:
                log.warning('%s', e)
                self.inotify = None
        else:
            self.inotify = None
        self.timer = None
        self.restart_timer = None
        self.restart_args = []
        self.last_checked = {}

        # If this env var is non-zero, initialize the update timer to
        # 0 so that we do initial indexing as quickly as possible.  Mainly
        # used for debugging/testing.
        if os.getenv("BEACON_EAT_CYCLES"):
            self.UPDATE_TIMER = 0
            self.PARSE_TIMER = 0

    def append(self, item):
        """
        Append a directory to be crawled and monitored.
        """
        log.info('crawl %s', item)
        self.restart_args.append(item)
        self.scan_directory(item)


    def stop(self):
        """
        Stop the crawler and remove the inotify watching.
        """
        self.finished()
        self.monitoring = []
        self.inotify = None
        for wait, timer in self.last_checked:
            if timer and timer.active():
                timer.stop()
        self.last_checked = {}
        

    # -------------------------------------------------------------------------
    # Internal functions
    # -------------------------------------------------------------------------
    
    def inotify_callback(self, mask, name, *args):
        """
        Callback for inotify.
        """
        if mask & INotify.MODIFY and name in self.last_checked and \
               self.last_checked[name][1]:
            # A file was modified. Do this check as fast as we can because the
            # events may come in bursts when a file is just copied. In this case
            # a timer is already active and we can return. It still uses too
            # much CPU time in the burst, but there is nothing we can do about
            # it.
            return True

        item = self.db.query(filename=name)

        if item._beacon_name.startswith('.'):
            # hidden file, ignore
            return True
        
        if mask & INotify.MOVE and args and item._beacon_id:
            # Move information with source and destination
            move = self.db.query(filename=args[0])
            if move._beacon_id:
                # New item already in the db, delete it first
                self.db.delete_object(move._beacon_id)
            changes = {}
            if item._beacon_parent._beacon_id != move._beacon_parent._beacon_id:
                # Different directory, set new parent
                changes['parent'] = move._beacon_parent._beacon_id
            if item._beacon_data['name'] != move._beacon_data['name']:
                # New name, set name to item
                changes['name'] = move._beacon_data['name']
            if changes:
                log.info('move: %s', changes)
                self.db.update_object(item._beacon_id, **changes)
            self.db.commit()

            # Now both directories need to be checked again
            self.scan_directory(item._beacon_parent, recursive=False)
            self.scan_directory(move._beacon_parent, recursive=False)

            if not mask & INotify.ISDIR:
                return True

            # The directory is a dir. We now remove all the monitors to that
            # directory and crawl it again. This keeps track for softlinks that
            # may be different or broken now.
            for m in self.monitoring[:]:
                if not m.startswith(name + '/'):
                    continue
                self.inotify.ignore(m)
                log.info('remove inotify for %s', m)
                self.monitoring.remove(m)
            # now make sure the directory is parsed recursive again
            self.scan_directory(move, recursive=True)
            return True

        if mask & INotify.MOVE and args:
            # We have a move with to and from, but the from item is not in
            # the db. So we handle it as a simple MOVE_TO
            name = args[0]
        
        if mask & INotify.CREATE or mask & INotify.DELETE or mask & INotify.MOVE:
            # directory changed, too
            self.scan_directory(item._beacon_parent, recursive=False)
        
        if os.path.exists(name):
            # The file exists. So it is either created or modified, we don't
            # care right now.
            if item._beacon_isdir:
                # It is a directory. Just do a full directory rescan.
                self.scan_directory(item, recursive=False)
                return True
            # Check if the item is already in our watch list
            for i in self.check_mtime_items:
                if i.filename == item.filename:
                    # already in the checking list, ignore it
                    return True
            for i, r in self.scan_directory_items:
                if i.filename == item._beacon_parent.filename:
                    # will be added later, ignore
                    return True

            now = time.time()
            if name in self.last_checked:
                last_check, timer = self.last_checked[name]
                if mask & INotify.CLOSE_WRITE:
                    # The file is closed. So we can remove the current running
                    # timer and check now
                    if timer:
                        timer.stop()
                    del self.last_checked[name]
                else:
                    # Do not check again, but restart the timer, it is expired
                    timer = OneShotTimer(self.inotify_timer_callback, name)
                    timer.start(GROWING_TIMER)
                    self.last_checked[name][1] = timer
                    return True
            elif INotify.MODIFY:
                # store the current time
                self.last_checked[name] = [ now, None ]
            if not mask & (INotify.CREATE | INotify.MOVE):
                # add to mtime checking when not CREATE or MOVE. When it is one
                # of these two, we already to a full directory rescan.
                self.check_mtime(item)
            return True

        # The file does not exist, we need to delete it in the database
        if self.db.get_object(item._beacon_data['name'],
                              item._beacon_parent._beacon_id):
            # Still in the db, delete it
            self.db.delete_object(item._beacon_id, beacon_immediately=True)
        # Remove item from list of files to check
        for i in self.check_mtime_items:
            if i.filename == item.filename:
                self.check_mtime_items.remove(i)
                break
        # remove directory and all subdirs from the inotify. The directory
        # is gone, so all subdirs are invalid, too.
        if name + '/' in self.monitoring:
            for m in self.monitoring[:]:
                # FIXME: This is not correct when you deal with softlinks. If you
                # move a directory with relative softlinks, the new directory to
                # monitor is different.
                if not m.startswith(name + '/'):
                    continue
                if self.inotify:
                    self.inotify.ignore(m)
                    log.info('remove inotify for %s', m)
                self.monitoring.remove(m)
        return True


    def inotify_timer_callback(self, name):
        """
        Callback for delayed inotify MODIFY events.
        """
        if not name in self.last_checked:
            return
        del self.last_checked[name]
        self.inotify_callback(INotify.MODIFY, name)


    def finished(self):
        """
        Crawler is finished with all directories and subdirectories and all
        files are now up to date.
        """
        if not self.timer:
            return
        log.info('crawler %s finished', self.num)
        Crawler.active -= 1
        self.timer.stop()
        self.timer = None
        self.scan_directory_items = []
        self.check_mtime_items = []
        self.update_items = []
        self.db.commit()
        if not self.inotify:
            # Inotify is not in use. This means we have to start crawling
            # the filesystem again in 10 seconds using the restart function.
            # The restart function will crawl with a much higher intervall to
            # keep the load on the system down.
            log.info('schedule rescan')
            self.restart_timer = OneShotTimer(self.restart).start(10)
                

    def restart(self):
        """
        Restart the crawler when inotify is not enabled.
        """
        # set parser time to one second to keep load down
        self.PARSE_TIMER = 1

        # reset self.monitoring and add all directories once passed to
        # this object with 'append' again.
        self.monitoring = []
        for item in self.restart_args:
            self.scan_directory(item)

        
    def scan_directory(self, directory=None, recursive=True):
        """
        Scan a directory for changes add all subitems to check_mtime. All
        subdirs are also added to scan_directory_items to be checked by this
        function later.
        """
        if directory:
            # add directory to the scanning list and if necessary start a timer
            # to do the scanning the mtime and the directory
            for entry in self.scan_directory_items:
                if directory.filename == entry[0].filename:
                    if recursive and not entry[1]:
                        entry[1] = True
                    break
            else:
                self.scan_directory_items.append([directory, recursive])
            self.check_mtime(directory)
            return True

        if not self.timer:
            # we should not run
            return False

        if not self.scan_directory_items:
            self.finished()
            return False

        item, recursive = self.scan_directory_items.pop(0)
        if not isinstance(item, Directory):
            log.warning('%s is no directory item', item)
            if hasattr(item, 'filename') and item.filename + '/' in self.monitoring:
                self.monitoring.remove(item.filename + '/')
            return True

        if not item.filename in self.monitoring and self.inotify:
            # add directory to the inotify list. Do that before the real checking
            # to avoid changes we would miss between checking and adding the
            # inotifier.
            dirname = item.filename[:-1]
            if item._beacon_islink:
                # WARNING: item is a link, we need to follow it
                dirname = os.path.realpath(item.filename)
            log.info('add inotify for %s' % dirname)
            try:
                self.inotify.watch(dirname, WATCH_MASK)
            except IOError, e:
                log.error(e)
                
        for child in self.db.query(parent=item):
            if child._beacon_isdir and recursive:
                # A directory. Check if it is already scanned or in the list of
                # items to be scanned. If not, add it.
                self.scan_directory(child)
                continue
            # add file to the list of items to be checked
            self.check_mtime(child)

        if not item.filename in self.monitoring:
            # add directory to list of files we scanned.
            self.monitoring.append(item.filename)

        # start checking the mtime of files
        self.check_mtime()
        return True


    def check_mtime(self, item=None):
        """
        Check the modification time of all items in self.check_mtime_items.
        This function will start a timer for check_mtime_step.
        """
        if item:
            for i in self.check_mtime_items:
                if i.filename == item.filename:
                    return True
            self.check_mtime_items.append(item)
            if not self.timer:
                Crawler.active += 1
                self.timer = Timer(self.check_mtime_step)
                self.timer.start(self.PARSE_TIMER / Crawler.active)
            return True

        # called without item, start stepping
        self.timer = Timer(self.check_mtime_step)
        self.timer.start(self.PARSE_TIMER / Crawler.active)

        
    def check_mtime_step(self):
        """
        Check the next up to 30 items for mtime changes. This function is called
        in a timer and will check all items in self.check_mtime_items. If it is
        done, it will call self.update to update all changed items.
        """
        if not self.timer:
            return False
        counter = 0
        while True:
            if not self.check_mtime_items:
                self.update()
                return False
            item = self.check_mtime_items.pop(0)
            counter += 1
            # log.info('mtime %s', item)
            if item._beacon_changed():
                self.update_items.append(item)
            if counter == 20 and len(self.check_mtime_items) > 10:
                return True


    def update(self):
        """
        Update all items that are changed. If no items is changed (anymore), call
        self.scan_directory to keep on crawling. This function will start a timer
        for update_step.
        """
        if self.update_items:
            self.timer = Timer(self.update_step)
            self.timer.start(self.UPDATE_TIMER / Crawler.active)
        else:
            self.timer = OneShotTimer(self.scan_directory)
            self.timer.start(self.PARSE_TIMER / 2)
        

    def update_step(self):
        """
        Update (parse) the first item in self.update_items. If the list is empty,
        call self.scan_directory to keep on crawling.
        """
        if not self.timer:
            return False
        if not self.update_items:
            self.scan_directory()
            return False
        # parse next item using parse from parser.py
        parse(self.db, self.update_items.pop(0))
        return True
