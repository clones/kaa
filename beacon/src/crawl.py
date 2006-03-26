import os
import logging

from kaa.notifier import Timer, OneShotTimer

import parser

log = logging.getLogger('crawler')

DIRECTORY_BLACKLIST  = [ '/usr/', '/bin/' ]
DIRECTORY_QUICKCHECK = [ '/', '/home/', os.path.expanduser("~/") ]

CHECK_TIMER  = 0.03
PARSE_TIMER  = 0.02
UPDATE_TIMER = 0.03

_crawling = []

class Crawler(object):

    active = 0
    nextid = 0
    
    def __init__(self, db):
        self.db = db
        self._checked = []
        self._tocheck = []
        self._toparse = []
        self._toupdate = []
        Crawler.nextid += 1
        self.num = Crawler.nextid
        

    def crawl(self, item):
        if not item.filename in DIRECTORY_QUICKCHECK + DIRECTORY_BLACKLIST:
            items = [ item ]
        else:
            items = self.search(item)
            
        for child in items:
            for c in _crawling:
                if child.filename.startswith(c):
                    break
            else:
                self._toparse.append(child)
                self._tocheck.append(child)
                _crawling.append(child.filename)
        if not self._toparse:
            return
        Crawler.active += 1
        log.info('start crawler %s for %s' % (self.num, [ x.filename for x in items]))
        self.timer = Timer(self.parse)
        self.timer.start(PARSE_TIMER / Crawler.active)


    def stop(self):
        if not self.timer:
            return
        log.info('crawler %s finished', self.num)
        Crawler.active -= 1
        self.timer.stop()
        self.timer = None
        for child in self._tocheck:
            if child.filename in _crawling:
                _crawling.remove(child.filename)
        self._tocheck = self._toparse = self._toupdate = []
        self.db.commit()

        
    def search(self, object):
        if not object._beacon_isdir or object.filename in DIRECTORY_BLACKLIST:
            return []
        if object._beacon_data['mtime'] and \
               not object.filename in DIRECTORY_QUICKCHECK:
            return [ object ]
        ret = []
        for child in self.db.query(parent=object):
            if not child._beacon_id:
                continue
            ret += self.search(child)
        return ret


    def check(self):
        if not self.timer:
            return False

        if not self._tocheck:
            self.stop()
            return False

        item = self._tocheck.pop(0)
        self._checked.append(item)
        log.debug('check %s', item)
        if item.filename in _crawling:
            _crawling.remove(item.filename)
        for child in self.db.query(parent=item):
            if child._beacon_isdir:
                for x in self._tocheck + self._checked:
                    if child.filename == x.filename:
                        self._toparse.append(child)
                        break
                else:
                    self._toparse.append(child)
                    self._tocheck.append(child)
                    _crawling.append(child.filename)
                continue
            self._toparse.append(child)
        self.timer = Timer(self.parse)
        self.timer.start(PARSE_TIMER / Crawler.active)
        return True


    def parse(self):
        if not self.timer:
            return False
        counter = 0
        while True:
            if not self._toparse:
                if self._toupdate:
                    self.timer = Timer(self.update)
                    self.timer.start(UPDATE_TIMER / Crawler.active)
                else:
                    self.timer = OneShotTimer(self.check)
                    self.timer.start(CHECK_TIMER / Crawler.active)
                return False
            item = self._toparse.pop(0)
            counter += 1
            if item._beacon_data['mtime'] != item._beacon_mtime():
                self._toupdate.append(item)
            if counter == 20 and len(self._toparse) > 10:
                return True


    def update(self):
        if not self.timer:
            return False
        if not self._toupdate:
            self.timer = OneShotTimer(self.check)
            self.timer.start(CHECK_TIMER / Crawler.active)
            return False
        item = self._toupdate.pop(0)
        parser.parse(self.db, item)
        return True
