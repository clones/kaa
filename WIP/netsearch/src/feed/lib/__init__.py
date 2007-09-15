import feedparser as _feedparser
import urllib2

import kaa.notifier

@kaa.notifier.execute_in_thread()
def feedparser(url):
    print url
    print _feedparser.parse
    return _feedparser.parse(urllib2.urlopen(url))
