import os
import logging

from kaa.base import ipc
from client import *
from server import *

__all__ = [ 'connect' ]

# connected client object
_client = None

def connect(epgdb, logfile='/tmp/kaa-epg.log', loglevel=logging.INFO):
    """
    """
    global _client

    # get server filename
    server = os.path.join(os.path.dirname(__file__), 'server.py')

    if epgdb.find(':') >= 0:
        # epg is remote:  host:port
        # TODO: create socket, pass it to client
        _client = GuideClient("epg")

    else:
        # epg is local
        _client = ipc.launch([server, logfile, str(loglevel), epgdb], 2, GuideClient, "epg")
    return _client


