import os
import re

from tvdb import TVDB
import imdb

REMOVE_FROM_SEARCH = []

def searchstring(filename):
    search = ''
    for part in re.split('[\._ -]', os.path.splitext(os.path.basename(filename))[0]):
        if part.lower() in REMOVE_FROM_SEARCH:
            break
        search += ' ' + part
    return search

def movie(search):
    return imdb.search(search)
