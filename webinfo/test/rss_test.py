# -*- coding: iso-8859-1 -*-

import sys
from types import *
import time

from kaa import main
from kaa.webinfo.urlcache import URLCache
from kaa.webinfo.rss import RssGrabber

testfeeds = [ 'http://participatoryculture.org/blog/wp-rss2.php',
              'https://channelguide.participatoryculture.org/?q=node/feed',
              'http://feevlog.com/bm/rss.php?i=2', ]

search_index = 0
              

# Some test classes for storing minimal information in the cache:

class RSSFeed(object):
    def __init__(self):
        self.title = None
        self.entries = []

    def __str__(self):
        return "%s (%d entries)" % (self.title, len(self.entries))


class RSSEntry(object):
    def __init__(self):
        self.title = None

    def __str__(self):
        return "%s" % self.title


def exception(e):
    print e

def parse_result(result):
    f = RSSFeed()
    f.title = result.feed['title']

    for entry in result.entries:
        e = RSSEntry()
        e.title = entry.title
        f.entries.append(e)

    print f

def print_status(s):
    print s
    
def print_progress(pos, length):
    if length:
        print pos, length, 100 * float(pos) / length
    else:
        print pos, length

def search_list(*args):
    global search_index
    if search_index < len(testfeeds):
        i.search(testfeeds[search_index])
        search_index += 1
    else:
        sys.exit(0)


i = RssGrabber()
i.signals['exception'].connect(exception)
i.signals['progress'].connect(print_progress)
i.signals['status'].connect(print_status)

i.signals['completed'].connect(parse_result)
i.signals['completed'].connect(search_list)

search_list()

main()

# cache = URLCache('/tmp/rsscache', hook_fetch=self.rss.search, hook_parse=self.parse_result)
# feed  = cache.get('http://participatoryculture.org/blog/wp-rss2.php')

