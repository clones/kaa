import os
import re

REMOVE_FROM_SEARCH = []

def searchstring(filename):
    search = ''
    for part in re.split('[\._ -]', os.path.splitext(os.path.basename(filename))[0]):
        if part.lower() in REMOVE_FROM_SEARCH:
            break
        try:
            if len(search) and int(part) > 1900 and int(part) < 2100:
                return search.strip(), int(part)
        except ValueError:
            pass
        search += ' ' + part
    return search.strip(), None

def movie(search):
    return imdb.search(search)
