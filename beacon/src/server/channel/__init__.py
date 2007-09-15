# ##################################################################
# Brain Dump
#
# - Improve RSS channel for better video and audio feed support
#   https://channelguide.participatoryculture.org/front
# - Flickr image channel
# - Torrent downloader (needed for some democracy channels)
# - Add more item metadata (e.g. download thumbnail/image)
# - Channel configuration:
#   o always download / download on demand / play from stream
#   o how much entries should be show
#   o keep entries on hd (while in feed / while not watched / up to x)
# - Add parallel download function
# - Add channel as 'file' to kaa.beacon making it possible to merge
#   feed entries and real files.
#   o does it belong into beacon?
#   o is it an extra kaa module with beacon plugin?
#   o daemon to keep feeds in beacon up-to-date
#
# ##################################################################

import kaa.rpc

import manager
import channel
import rss

@kaa.rpc.expose('channels.update')
def update(id=None):
    if id == None:
        return manager.update()
    for c in manager.list_channels():
        if id == c.id:
            return c.update()
    return False
    
@kaa.rpc.expose('channels.list')
def list_channels():
    channels = []
    for c in manager.list_channels():
        channels.append(c.get_config())
    return channels

@kaa.rpc.expose('channels.add')
def add_channel(url, destdir, download=True, num=0, keep=True):
    return manager.add_channel(url, destdir, download, num, keep).get_config()

@kaa.rpc.expose('channels.remove')
def remove_channel(id):
    for c in manager.list_channels():
        if id == c.id:
            manager.remove_channel(c)
            return True
    return False

def set_database(database):
    channel.Channel._db = database
    manager.init()
