import os
import logging
from xml.dom import minidom

import kaa.notifier
from kaa.strutils import unicode_to_str

# fallback RSS parser
import rss

# get logging object
log = logging.getLogger('beacon.channel')

CACHE = os.path.expanduser("~/.beacon/channels.xml")

# list of all channel objects
_channels = []

# list of all Channel classes
_generators = []

def register(regexp, generator):
    """
    Register a Channel class.
    """
    _generators.append((regexp, generator))


def _get_channel(url, destdir):
    """
    Get channel class from generators and create the channel object.
    """
    for regexp, generator in _generators:
        if regexp.match(url):
            return generator(url, destdir)
    return rss.Channel(url, destdir)


def add_channel(url, destdir, download=True, num=0, keep=True):
    """
    Add a new channel.
    """
    for c in _channels:
        if c.dirname == destdir and c.url == url:
            raise RuntimeError('channel already exists')
    channel = _get_channel(url, destdir)
    _channels.append(channel)
    channel.configure(download, num, keep)
    return channel


def list_channels():
    """
    Return a list of all channels.
    """
    return _channels


def remove_channel(channel):
    """
    Remove a channel.
    """
    _channels.remove(channel)
    channel.remove()
    save()
    

def save():
    """
    Save all channel information
    """
    doc = minidom.getDOMImplementation().createDocument(None, "channels", None)
    top = doc.documentElement
    for c in _channels:
        node = doc.createElement('channel')
        c._writexml(node)
        top.appendChild(node)
    f = open(CACHE, 'w')
    f.write(doc.toprettyxml())
    f.close()

    
def init():
    """
    Load cached channels from disc.
    """

    def parse_channel(c):
        for d in c.childNodes:
            if not d.nodeName == 'directory':
                continue
            dirname = unicode_to_str(d.childNodes[0].data.strip())
            url = unicode_to_str(c.getAttribute('url'))
            channel = _get_channel(url, dirname)
            channel._readxml(c)
            _channels.append(channel)
            return
        
    if not os.path.isfile(CACHE):
        return

    try:
        cache = minidom.parse(CACHE)
    except:
        log.exception('bad cache file: %s' % CACHE)
        return
    if not len(cache.childNodes) == 1 or \
           not cache.childNodes[0].nodeName == 'channels':
        log.error('bad cache file: %s' % CACHE)
        return

    for c in cache.childNodes[0].childNodes:
        try:
            parse_channel(c)
        except:
            log.exception('bad cache file: %s' % CACHE)


_updating = False

@kaa.notifier.yield_execution()
def update(verbose=False):
    """
    Update all channels
    """
    global _updating
    if _updating:
        log.error('update already in progress')
        yield False
    log.info('start channel update')
    _updating = True
    for channel in _channels:
        x = channel.update(verbose=verbose)
        yield x
        log.info('XXXXXXXXX')
        x()
    _updating = False
    yield True
