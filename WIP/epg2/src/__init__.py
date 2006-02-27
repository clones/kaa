import os
import logging
from socket import gethostbyname, gethostname

from kaa.base import ipc
from client import *
from server import *

__all__ = [ 'connect', 'DEFAULT_EPG_PORT', 'GuideClient', 'GuideServer' ]

# connected client object
_client = None

def connect(epgdb, address='127.0.0.1', logfile='/tmp/kaa-epg.log', loglevel=logging.INFO):
    """
    """
    global _client

    if _client:
        return _client

    if address.split(':')[0] not in ['127.0.0.1', '0.0.0.0'] and \
       address.split(':')[0] != gethostbyname(gethostname()):
        # epg is remote:  host:port
        if address.find(':') >= 0:
            host, port = address.split(':', 1)
        else:
            host = address
            port = DEFAULT_EPG_PORT

        # create socket, pass it to client
        _client = GuideClient((host, int(port)))

    else:
        # EPG is local, only use unix socket

        # get server filename
        server = os.path.join(os.path.dirname(__file__), 'server.py')

        _client = ipc.launch([server, logfile, str(loglevel), epgdb, address], 
                              2, GuideClient, "epg")

    return _client


