import os
import logging

from kaa.notifier import Timer, OneShotTimer

import parser
from inotify import INotify
from directory import Directory

log = logging.getLogger('crawler')

class Crawler(object):

    PARSE_TIMER  = 0.02
    UPDATE_TIMER = 0.03

    active = 0
    nextid = 0
    
    def __init__(self, db):
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
        try:
            self.inotify = INotify()
        except SystemError, e:
            log.warning('%s', e)
            self.inotify = None
        self.timer = None
        self.restart_timer = None
        self.restart_args = []


    def inotify_callback(self, mask, name):
        if mask & INotify.WATCH_MASK:
            item = self.db.query(filename=name)
            if os.path.exists(name):
                # created or modified, we don't care
                if item._beacon_isdir:
                    self.scan_directory_items.append(item)
                self.check_mtime_items.append(item)
                if not self.timer:
                    Crawler.active += 1
                    self.check_mtime()
            else:
                # deleted
                item = self.db.query(filename=name)
                if item._beacon_id:
                    self.db.delete_object(item._beacon_id, beacon_immediately=True)
                if name + '/' in self.monitoring:
                    for m in self.monitoring[:]:
                        if m.startswith(name + '/'):
                            if self.inotify:
                                self.inotify.ignore(m)
                                log.info('remove inotify for %s', m)
                            self.monitoring.remove(m)

    def append(self, item):
        log.info('crawl %s', item)
        self.check_mtime_items.append(item)
        self.scan_directory_items.append(item)
        self.restart_args.append(item)
        if not self.timer:
            Crawler.active += 1
            log.info('start crawler %s' % self.num)
            self.check_mtime()


    def finished(self):
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
            log.info('schedule rescan')
            self.restart_timer = OneShotTimer(self.restart).start(10)
                

    def stop(self):
        self.finished()
        self.monitoring = []
        self.inotify = None
        
        
    def restart(self):
        self.PARSE_TIMER = 1

        self.monitoring = []
        for item in self.restart_args:
            self.check_mtime_items.append(item)
            self.scan_directory_items.append(item)
        Crawler.active += 1
        log.info('start crawler %s' % self.num)
        self.check_mtime()

        
    def scan_directory(self):
        if not self.timer:
            return False

        if not self.scan_directory_items:
            self.finished()
            return False

        item = self.scan_directory_items.pop(0)
        if not isinstance(item, Directory):
            log.warning('%s is no directory item', item)
            if hasattr(item, 'filename') and item.filename + '/' in self.monitoring:
                self.monitoring.remove(item.filename + '/')
            return True

        log.debug('check %s', item)
        for child in self.db.query(parent=item):
            if child._beacon_isdir:
                for fname in [ f.filename for f in self.scan_directory_items ] + \
                        self.monitoring:
                    if child.filename == fname:
                        self.check_mtime_items.append(child)
                        break
                else:
                    self.check_mtime_items.append(child)
                    self.scan_directory_items.append(child)
                continue
            self.check_mtime_items.append(child)
        if not item.filename in self.monitoring:
            if self.inotify:
                log.info('add inotify for %s' % item.filename)
                self.inotify.watch(item.filename[:-1]).connect(self.inotify_callback)
            self.monitoring.append(item.filename)
        self.check_mtime()
        return True


    def check_mtime(self):
        self.timer = Timer(self.check_mtime_step)
        self.timer.start(self.PARSE_TIMER / Crawler.active)

        
    def check_mtime_step(self):
        if not self.timer:
            return False
        counter = 0
        while True:
            if not self.check_mtime_items:
                self.update()
                return False
            item = self.check_mtime_items.pop(0)
            counter += 1
            if item._beacon_data['mtime'] != item._beacon_mtime():
                self.update_items.append(item)
            if counter == 20 and len(self.check_mtime_items) > 10:
                return True


    def update(self):
        if self.update_items:
            self.timer = Timer(self.update_step)
            self.timer.start(self.UPDATE_TIMER / Crawler.active)
        else:
            self.scan_directory()
        

    def update_step(self):
        if not self.timer:
            return False
        if not self.update_items:
            self.scan_directory()
            return False
        item = self.update_items.pop(0)
        parser.parse(self.db, item)
        return True
