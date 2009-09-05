import os

themoviedb = None
thetvdb = None

def init():
    global themoviedb
    import themoviedb as backend
    themoviedb = backend.MovieDB(os.path.expanduser("~/.beacon/moviedb"))
    global thetvdb
    import tvdb as backend
    thetvdb = tvdb.TVDB(os.path.expanduser("~/.beacon/tvdb"))

def parse(filename):
    series = thetvdb.from_filename(filename)
    if series.series and series.episode:
        return series.episode
    movie = themoviedb.from_filename(filename)
    if movie.available:
        return movie._movie
    return None
