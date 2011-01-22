import os
import kaa
import kaa.metadata

backends = {}

WORKER_THREAD = 'WEBMETADATA'

kaa.metadata.enable_feature('VIDEO_SERIES_PARSER')

def init(base='~/'):
    if not backends:
        import themoviedb as backend
        backends['themoviedb'] = backend.MovieDB(os.path.expanduser(base + '/themoviedb'))
        import thetvdb as backend
        backends['thetvdb'] = backend.TVDB(os.path.expanduser(base + '/thetvdb'))

def parse(filename, metadata=None):
    if filename.startswith('thetvdb:'):
        info = backends['thetvdb']._get_series_by_name(kaa.py3_str(filename[8:]))
        if info:
            return 'thetvdb', info
        return None
    if not metadata:
        metadata = kaa.metadata.parse(filename)
    if getattr(metadata, 'series', None):
        info = backends['thetvdb']._get_series_by_name(metadata.series)
        if info:
            if getattr(metadata, 'season', None) and getattr(metadata, 'episode'):
                info = info.get_season(metadata.season).get_episode(metadata.episode)
            return 'thetvdb', info
    movie = backends['themoviedb'].from_filename(filename)
    if movie.available:
        return 'themoviedb', movie._movie
    return None

def search(filename, metadata=None):
    for module in backends.values():
        if filename.startswith(module.scheme):
            return module.search(filename[len(module.scheme):])
    if not metadata:
        metadata = kaa.metadata.parse(filename)
    if getattr(metadata, 'series', None):
        return backends['thetvdb'].search(metadata.series)
    return []

def match(filename, id, metadata=None):
    parser, id = id.split(':')
    for module in backends.values():
        if filename.startswith(module.scheme):
            return module.match(filename[len(module.scheme):], id)
    if not metadata:
        metadata = kaa.metadata.parse(filename)
    if parser in ('thetvdb', ):
        return backends[parser].match(metadata.series, int(id))

def set_metadata(key, value):
    for module in backends.values():
        if key.startswith(module.scheme):
            return module.set_metadata(key[len(module.scheme):], value)
    for module in backends.values():
        module.set_metadata(key, value)

def get_metadata(key):
    for module in backends.values():
        if key.startswith(module.scheme):
            return module.get_metadata(key[len(module.scheme):])
    for module in backends.values():
        value = module.get_metadata(key)
        if value is not None:
            return value

kaa.register_thread_pool(WORKER_THREAD, kaa.ThreadPool())
