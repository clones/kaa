import os
import logging

from kaa.db import QExpr

from channel import Channel
from program import Program
from client import Client
from server import Server
from util import cmp_channel
from source import sources

__all__ = [ 'connect', 'Channel', 'Program', 'Client', 'Server', 'QExpr',
            'get_channels', 'get_channel', 'search', 'sources' ]

log = logging.getLogger('epg')

# connected client object
guide = None

def connect(address, auth_secret=None):
    """
    """
    global guide
    
    if guide and guide.connected:
        log.warning('connecting to a new epg database')

    guide = Client(address, auth_secret)
    return guide


def get_channels(sort=False):
    if guide:
        if sort:
            channels = guide.get_channels()[:]
            channels.sort(lambda a, b: cmp(a.name, b.name))
            channels.sort(lambda a, b: cmp_channel(a, b))
            return channels
        return guide.get_channels()
    return []


def get_channel(*args, **kwargs):
    if guide:
        return guide.get_channel(*args, **kwargs)
    return []


def search(*args, **kwargs):
    if guide:
        try:
            return guide.search(*args, **kwargs)
        except Exception, e:
            log.exception('kaa.epg.search failed')
    return []
