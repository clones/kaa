import os
import logging
from xml.dom import minidom

import kaa.notifier
from kaa.strutils import unicode_to_str

# get logging object
log = logging.getLogger('beacon.channel')

CACHE = os.path.expanduser("~/.beacon/channels.xml")

_initialized = False

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
    raise RuntimeError


def add_channel(url, destdir, download=True, num=0, keep=True):
    """
    Add a new channel.
    """
    if not _initialized:
        _init()
    for c in _channels:
        if c.dirname == destdir and c.url == url:
            raise RuntimeError('channel already exists')
    channel = _get_channel(url, destdir)
    _channels.append(channel)
    channel.configure(download, num, keep)


def list_channels():
    """
    Return a list of all channels.
    """
    if not _initialized:
        _init()
    return _channels


def remove_channel(channel):
    """
    Remove a channel.
    """
    _channels.remove(channel)
    save()
    

def save():
    """
    Save all channel information
    """
    if not _initialized:
        _init()
    doc = minidom.getDOMImplementation().createDocument(None, "channels", None)
    top = doc.documentElement
    for c in _channels:
        node = doc.createElement('channel')
        c._writexml(node)
        top.appendChild(node)
    f = open(CACHE, 'w')
    f.write(doc.toprettyxml())
    f.close()

    
def _init():
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
        
    global _initialized
    _initialized = True
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
        yield False
    if not _initialized:
        _init()
    _updating = True
    for channel in _channels:
        yield channel.update(verbose=verbose)
    _updating = False
    yield True
