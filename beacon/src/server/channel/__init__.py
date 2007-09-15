# ##################################################################
# Brain Dump
#
# - Improve RSS feed for better video and audio feed support
#   https://feedguide.participatoryculture.org/front
# - Flickr image feed
# - Torrent downloader (needed for some democracy feeds)
# - Add more item metadata (e.g. download thumbnail/image)
# - Feed configuration:
#   o always download / download on demand / play from stream
#   o how much entries should be show
#   o keep entries on hd (while in feed / while not watched / up to x)
# - Add parallel download function
# - Add feed as 'file' to kaa.beacon making it possible to merge
#   feed entries and real files.
#   o does it belong into beacon?
#   o is it an extra kaa module with beacon plugin?
#   o daemon to keep feeds in beacon up-to-date
#
# ##################################################################

import kaa.rpc

import manager
import feed
import rss

@kaa.rpc.expose('feeds.update')
def update(id=None):
    if id == None:
        return manager.update()
    for c in manager.list_feeds():
        if id == c.id:
            return c.update()
    return False
    
@kaa.rpc.expose('feeds.list')
def list_feeds():
    feeds = []
    for c in manager.list_feeds():
        feeds.append(c.get_config())
    return feeds

@kaa.rpc.expose('feeds.add')
def add_feed(url, destdir, download=True, num=0, keep=True):
    return manager.add_feed(url, destdir, download, num, keep).get_config()

@kaa.rpc.expose('feeds.remove')
def remove_feed(id):
    for c in manager.list_feeds():
        if id == c.id:
            manager.remove_feed(c)
            return True
    return False

def set_database(database):
    feed.Feed._db = database
    manager.init()
