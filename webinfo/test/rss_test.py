# -*- coding: iso-8859-1 -*-

import sys
from types import *
import time

from kaa.webinfo.urlcache import URLCache
from kaa.webinfo.rss import RssGrabber
from kaa.webinfo.lib.feedparser import FeedParserDict


class RSSFeed(object):
    """
    feed: 
     tagline_detail
     generator
     links
     title
     tagline
     modified
     language
     title_detail
     link
     modified_parsed
    """
    
    def __init__(self):
        self.bozo = None
        self.encoding = None
        self.version = None
        self.entries = []
        self.link = None
        self.title = None


class RSSEntry(object):
    """
        category
        summary_detail
        modified_parsed
        description
        links
        title
        author
        modified
        comments
        summary
        content
        guidislink
        title_detail
        link
        wfw_commentrss
        id
        categories
    """

    def __init__(self):
        self.title = None
        self.title_detail = None
        self.description = None


    def __str__(self):
        return "%s: %s" % (self.title, self.title_detail)


class RssTest:

    def __init__(self):
        # self.rss = RssGrabber(cb_progress=self.rss_progress, cb_result=self.rss_result)
        # self.rss = RssGrabber(cb_progress=self.rss_progress)
        self.rss = RssGrabber()
        # res = self.rss.search('http://participatoryculture.org/blog/wp-rss2.php')
        # self.rss.search('http://feevlog.com/bm/rss.php?i=2')

        cache = URLCache('/tmp/rsscache', hook_fetch=self.rss.search, hook_parse=self.parse_result)
        tick = time.time()
        feed = cache.get('http://participatoryculture.org/blog/wp-rss2.php')
        print 'get 1 took %s' % (time.time() - tick)
        tick = time.time()
        feed = cache.get('http://feevlog.com/bm/rss.php?i=2')
        print feed
        print dir(feed)
        print feed.title
        print feed.entries[0]
        print 'get 2 took %s' % (time.time() - tick)
        tick = time.time()
        # feed = cache.get('http://tvcentric.com/bm/rss.php?i=2')
        feed = cache.get('https://channelguide.participatoryculture.org/?q=node/feed')
        print 'get 3 took %s' % (time.time() - tick)


    def rss_progress(self, percent):
        print 'tick: %d%%' % percent


    def parse_result(self, result):
        f = RSSFeed()
        f.title = result.feed['title']

        for entry in result.entries:
            e = RSSEntry()
            e.title = entry.title
            f.entries.append(e)
            print 'E: %s' % entry

        return f


    def rss_result(self, result):
        # print dir(result)
        print result.keys()
        for k,v in result.items():
            print '#######################################'
            # print '%s:  %s' % (k, v)
            print '%s: ' % k
            # print 'type: %s' % type(v)
            if type(v) is FeedParserDict:
                for i,j in v.items():
                    print '    %s' % i
            elif type(v) is ListType:
                for i in v:
                    print '    #######################################'
                    # print '    %s' % i
                    if type(i) is FeedParserDict:
                        # print 'enclosures: %s' % i.enclosures
                        for l,m in i.items():
                            print '        %s' % l
            else:
                print '    %s' % v

        print result.feed
        sys.exit(0)


rt = RssTest()
# kaa.notifier.loop()

