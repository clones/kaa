from kaa.db import QExpr

from channel import Channel
from program import Program
from client import Client
from server import Server

__all__ = [ 'connect', 'Channel', 'Program', 'Client', 'Server', 'QExpr',
            'get_channels', 'search' ]

# connected client object
guide  = None
_address = None

def connect(address, auth_secret=None):
    """
    """
    global guide
    global _address
    
    if guide and guide.connected and _address == address:
        return guide

    guide = Client(address, auth_secret)
    _address = address
    return guide


def get_channels():
    if guide:
        return guide.get_channels()
    return []


def get_channel(*args, **kwargs):
    if guide:
        return guide.get_channel(*args, **kwargs)
    return []


def search(*args, **kwargs):
    if guide:
        return guide.search(*args, **kwargs)
    return []
