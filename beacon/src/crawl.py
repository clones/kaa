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
import kaa.notifier
from kaa.notifier import Timer, OneShotTimer, WeakOneShotTimer, YieldFunction

# kaa.beacon imports
from parser import parse
from kaa.inotify import INotify
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

class MonitorList(dict):

    def __init__(self, inotify):
        dict.__init__(self)
        self._inotify = inotify

    def add(self, dirname, use_inotify=True):
        if self._inotify and use_inotify:
            log.info('add inotify for %s' % dirname)
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
                if s.startswith(dirname):
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
    PARSE_TIMER  = 0.04

    active = 0
    nextid = 0
    
    def __init__(self, db, use_inotify=True):
        """
        Init the Crawler.
        Parameter db is a beacon.db.Database object.
        """
        self.db = db
        Crawler.nextid += 1
        self.num = Crawler.nextid

        # set up inotify
        self._inotify = None
        self._inotify_timer = {}
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
        if os.getenv("BEACON_EAT_CYCLES"):
            log.info('all your cpu are belong to me')
            self.PARSE_TIMER = 0

        kaa.signals["shutdown"].connect_weak(self.stop)

        # create internal scan variables
        self._scan_list = []
        self._scan_dict = {}
        self._scan_function = None
        self._scan_restart_timer = None

        
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
        kaa.signals["shutdown"].disconnect(self.stop)
        # stop running scan process
        self._scan_list = []
        self._scan_dict = []
        if self._scan_function:
            self._scan_function.stop()
            self._scan_function = None
            self._scan_stop([], False)
        # stop inotify and inotify timer
        self._inotify = None
        for wait, timer in self._inotify_timer.items():
            if timer and timer.active():
                timer.stop()
        self._inotify_timer = {}
        # stop restart timer
        if self._scan_restart_timer:
            self._scan_restart_timer.stop()
            self._scan_restart_timer = None
            

    def __del__(self):
        print 'del', self

        
    def __repr__(self):
        return '<kaa.beacon.Crawler>'

    # -------------------------------------------------------------------------
    # Internal functions - INotify
    # -------------------------------------------------------------------------
    
    def _inotify_event(self, mask, name, *args):
        """
        Callback for inotify.
        """
        if mask & INotify.MODIFY and name in self._inotify_timer and \
               self._inotify_timer[name][1]:
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

        # ---------------------------------------------------------------------
        # MOVE_FROM -> MOVE_TO
        # ---------------------------------------------------------------------
        
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
            self._scan_add(item._beacon_parent, recursive=False)
            self._scan_add(move._beacon_parent, recursive=False)

            if not mask & INotify.ISDIR:
                return True

            # The directory is a dir. We now remove all the monitors to that
            # directory and crawl it again. This keeps track for softlinks that
            # may be different or broken now.
            self.monitoring.remove(name + '/', recursive=True)
            # now make sure the directory is parsed recursive again
            self._scan_add(move, recursive=True)
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
                self._scan_add(item, recursive=False)
                return True

            # handle bursts of inotify events when a file is growing very
            # fast (e.g. cp)
            now = time.time()
            if name in self._inotify_timer:
                last_check, timer = self._inotify_timer[name]
                if mask & INotify.CLOSE_WRITE:
                    # The file is closed. So we can remove the current running
                    # timer and check now
                    if timer:
                        timer.stop()
                    del self._inotify_timer[name]
                else:
                    # Do not check again, but restart the timer, it is expired
                    timer = OneShotTimer(self._inotify_timer_callback, name)
                    timer.start(GROWING_TIMER)
                    self._inotify_timer[name][1] = timer
                    return True
            elif INotify.MODIFY:
                # store the current time
                self._inotify_timer[name] = [ now, None ]

            # parent directory changed, too. Even for a simple modify of an
            # item another item may be affected (xml metadata, images)
            # so scan the file by rechecking the parent dir
            self._scan_add(item._beacon_parent, recursive=False)
            return True

        # ---------------------------------------------------------------------
        # DELETE
        # ---------------------------------------------------------------------

        # The file does not exist, we need to delete it in the database
        if self.db.get_object(item._beacon_data['name'],
                              item._beacon_parent._beacon_id):
            # Still in the db, delete it
            self.db.delete_object(item._beacon_id, beacon_immediately=True)

        # remove directory and all subdirs from the inotify. The directory
        # is gone, so all subdirs are invalid, too.
        if name + '/' in self.monitoring:
            # FIXME: This is not correct when you deal with softlinks.
            # If you move a directory with relative softlinks, the new
            # directory to monitor is different.
            self.monitoring.remove(name + '/', recursive=True)
        # rescan parent directory
        self._scan_add(item._beacon_parent, recursive=False)
        return True


    def _inotify_timer_callback(self, name):
        """
        Callback for delayed inotify MODIFY events.
        """
        if not name in self._inotify_timer:
            return
        del self._inotify_timer[name]
        self._inotify_event(INotify.MODIFY, name)


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
            self._scan_function = OneShotTimer(self._scan_start)
            self._scan_function.start(0)
            

    def _scan_start(self):
        """
        Start the scan function using YieldFunction.
        """
        interval = self.PARSE_TIMER / Crawler.active
        self._scan_function = YieldFunction(self._scan, interval)
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
        log.info('crawler %s finished', self.num)
        Crawler.active -= 1
        self.db.commit()
        if not self._inotify:
            # Inotify is not in use. This means we have to start crawling
            # the filesystem again in 10 seconds using the restart function.
            # The restart function will crawl with a much higher intervall to
            # keep the load on the system down.
            log.info('schedule rescan')
            self._scan_restart_timer = WeakOneShotTimer(self._scan_restart)
            self._scan_restart_timer.start(10)


    def _scan_restart(self):
        """
        Restart the crawler when inotify is not enabled.
        """
        # set parser time to one second to keep load down
        self.PARSE_TIMER = 1

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
        
        # parse directory
        if parse(self.db, directory):
            yield kaa.notifier.YieldContinue

        # check if it is still a directory
        if not isinstance(directory, Directory):
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
            directory = self.db.query(filename=dirname)
            if parse(self.db, directory):
                yield kaa.notifier.YieldContinue

        # add to monitor list using inotify
        self.monitoring.add(directory.filename)
                
        # iterate through the files
        subdirs = []
        counter = 0
        for child in self.db.query(parent=directory):
            if child._beacon_isdir:
                # add directory to list of files to return
                subdirs.append(child)
                continue
            # check file
            counter += parse(self.db, child) * 20
            while counter >= 20:
                counter -= 20
                yield kaa.notifier.YieldContinue
            counter += 1
        yield subdirs
