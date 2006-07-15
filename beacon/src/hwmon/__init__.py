import time
import socket

import kaa.notifier

from hwmon import Client as _Client
from media import medialist

_client = None

def connect():
    """
    Connect to hardware monitor process. This function will block
    if connection is not possible (timeout 3 sec).
    """
    global _client
    if _client:
        return _client
    start = time.time()
    while True:
        try:
            _client = _Client()
            return _client
        except socket.error, e:
            if start + 3 < time.time():
                # start time is up, something is wrong here
                raise RuntimeError('unable to connect to hardware monitor')
            time.sleep(0.01)


def set_database(handler, db, rootfs=None):
    if not _client:
        connect()
    _client.set_database(handler, db, rootfs)
