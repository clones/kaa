import os
import kaa
import kaa.metadata

backends = {}

WORKER_THREAD = 'WEBMETADATA'

kaa.metadata.enable_feature('VIDEO_SERIES_PARSER')
kaa.register_thread_pool(WORKER_THREAD, kaa.ThreadPool())

from core import Movie, Series, Season, Episode

def init(base='~/.beacon'):
    """
    Initialize the kaa.webmetadata databases
    """
    if backends:
        return
    import thetvdb as backend
    backends['thetvdb'] = backend.TVDB(os.path.expanduser(base + '/thetvdb'))
    import themoviedb as backend
    backends['themoviedb'] = backend.MovieDB(os.path.expanduser(base + '/themoviedb'))

def db_version():
    """
    Get database version
    """
    ver = 0
    for module in backends.values():
        ver += module.version
    return ver

def parse(filename, metadata=None):
    """
    Parse the given filename and return information from the db. If
    metadata is None it will be created using kaa.metadata. Each
    dictionary-like object is allowed.
    """
    if not metadata:
        metadata = kaa.metadata.parse(filename)
    if metadata.get('series', None):
        info = backends['thetvdb'].parse(filename, metadata)
        if info:
            if metadata.get('season', None) and metadata.get('episode'):
                info = info.get_season(metadata.get('season')).get_episode(metadata.get('episode'))
            return info
    return backends['themoviedb'].parse(filename, metadata)

def search(filename, metadata=None):
    """
    Search the given filename in the web. If metadata is None it will
    be created using kaa.metadata. Each dictionary-like object is
    allowed.
    """
    if not metadata:
        metadata = kaa.metadata.parse(filename)
    if metadata.get('series', None):
        return backends['thetvdb'].search(metadata.get('series'))
    return backends['themoviedb'].search(filename, metadata)

def match(filename, id, metadata=None):
    """
    Match the given filename with the id for future parsing. If
    metadata is None it will be created using kaa.metadata. Each
    dictionary-like object is allowed.
    """
    parser, id = id.split(':')
    if not metadata:
        metadata = kaa.metadata.parse(filename)
    metadata.filesize = os.path.getsize(filename)
    return backends[parser].match(metadata, int(id))

@kaa.coroutine()
def sync():
    """
    Sync the databases with their web counterparts
    """
    for module in backends.values():
        yield module.sync()

def set_metadata(key, value):
    """
    Store some metadata in the database
    """
    for module in backends.values():
        module.set_metadata(key, value)

def get_metadata(key):
    """
    Retrive stored metadata
    """
    for module in backends.values():
        value = module.get_metadata(key)
        if value is not None:
            return value
