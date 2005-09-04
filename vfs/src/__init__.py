from db import Database, ATTR_SIMPLE, ATTR_SEARCHABLE, ATTR_INDEXED, ATTR_KEYWORDS
from mediadb import MediaDB

_db = None

def _error(*args, **kwargs):
    raise RuntimeError('not connected to database')

query = listdir = file = commit = _error

def connect(filename):
    global _db
    if _db:
        raise RuntimeError('already connected')
    _db = MediaDB(filename)

    global query
    global listdir
    global file
    global commit
    
    query = _db.do_query
    listdir = _db.listdir
    file = _db.file
    commit = _db.commit
    
