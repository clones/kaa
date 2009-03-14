import os
import re
import sys
import urllib
import urllib2
import logging
from BeautifulSoup import BeautifulSoup as BeautifulSoupOriginal, NavigableString
import HTMLParser

import kaa
from kaa.saxutils import Element, pprint

log = logging.getLogger('imdb')
log.setLevel(logging.DEBUG)

txdata = None
txheaders = {
    'User-Agent': 'Kaa (%s)' % sys.platform,
    'Accept-Language': 'en-us',
}

class Result(object):
    def __init__(self, id, title, year, type):
        self.imdb = id
        self.title = title
        self.year = year

    def fetch(self):
        return fetch(self.imdb)

class BeautifulSoup(BeautifulSoupOriginal):
    def _convert_ref(self, match):
        ref = BeautifulSoupOriginal._convert_ref(self, match)
        return kaa.str_to_unicode(ref)

@kaa.threaded()
def search(name):
    """
    Search IMDB for the name

    :param name: name to search for
    :type name: string
    :returns: id list with tuples (id, name, year, type)
    """
    name = name.strip()
    url = 'http://www.imdb.com/find?s=tt;site=aka;q=%s' % urllib.quote(str(name))
    req = urllib2.Request(url, txdata, txheaders)
    searchstring = name
    try:
        response = urllib2.urlopen(req)
    except urllib2.HTTPError, error:
        raise IOError("IMDB unreachable : " + error)
    m = re.compile('/title/tt([0-9]*)/')
    idm = m.search(response.geturl())
    if idm: # Direct Hit
        id = idm.group(1)
        response.close()
        return [Result(id, name.title(), u'', '')]
    results = [ Result(*args) for args in parsesearchdata(response) ]
    for part in re.split('[\._ -]', searchstring):
        if part in [ result.year for result in results ]:
            new = search(searchstring.replace(part, '(%s)' % part))
            for old in results:
                if old.imdb not in [ x.imdb for x in new ]:
                    new.append(old)
            results = new
            break
    response.close()
    if len(results) > 20:
        # too many results, check if there are stupid results in the list
        # make a list of all words (no numbers) in the search string
        words = re.split('[\._ -]', searchstring)
        # at least one word has to be in the result
        new_list = []
        for result in results:
            for search_word in words:
                if result.title and result.title.lower().find(search_word.lower()) != -1:
                    new_list.append(result)
                    break
        results = new_list
        log.debug('id_list has now %s items', len(results))
    return results


def parsesearchdata(results):
    """
    :returns: tuple of (title, info(dict))
    """
    log.debug('parsesearchdata(results=%r)', results)
    id_list = []
    m = re.compile('/title/tt([0-9]*)/')
    y = re.compile('\(([^)]+)\)')
    try:
        soup = BeautifulSoup(results.read(), convertEntities='xml')
    except (HTMLParser.HTMLParseError, UnicodeDecodeError), e:
        log.exception('unable to parse %s', response.geturl())
        return []
    items = soup.findAll('a', href=re.compile('/title/tt'))
    ids = set([])
    for item in items:
        idm = m.search(item['href'])
        if not idm:
            continue
        if isinstance(item.next.next, NavigableString):
            yrm = y.findall(item.next.next)
        id = idm.group(1)
        name = item.string
        # skip empty names
        if not name:
            continue
        # skip duplicate ids
        if id in ids:
            continue
        ids.add(id)
        year = len(yrm) > 0 and yrm[0] or '0000'
        type = len(yrm) > 1 and yrm[1] or ''
        id_list += [ ( id, name, year, type ) ]
    return id_list


@kaa.threaded()
def fetch(id):
    """
    Set an imdb_id number for object, and fetch data
    """
    url = 'http://www.imdb.com/title/tt%s' % id
    req = urllib2.Request(url, txdata, txheaders)
    try:
        idpage = urllib2.urlopen(req)
    except urllib2.HTTPError, why:
        raise IOError('IMDB unreachable' + str(why))
    info = parse_data(idpage, id)
    idpage.close()
    info['source'] = url
    info['id'] = id
    return info


def parse_data(results, id):
    """
    Returns tuple of (title, info(dict))
    """
    soup = BeautifulSoup(results.read(), convertEntities='xml')
    info = {}
    # The parse tree can be now reduced by, everything outside this is not required:
    main = soup.find('div', {'id': 'tn15main'})
    soup_title = soup.find('h1')
    title = soup_title.next.strip()
    info['year'] = soup_title.find('a').string.strip()
    info['title'] = title
    # Find the <div> with class info, each <h5> under this provides info
    for soup_info in main.findAll('div', {'class' : 'info'}):
        infoh5 = soup_info.find('h5')
        if not infoh5:
            continue
        try:
            infostr = infoh5.next
            key = infostr.string.strip(':').lower().replace(' ', '_')
            nextsibling = nextsibling = infoh5.nextSibling.strip()
            sections = soup_info.findAll('a', { 'href' : re.compile('/Sections') })
            lists = soup_info.findAll('a', { 'href' : re.compile('/List') })
            if len(nextsibling) > 0:
                info[key] = nextsibling
            elif len(sections) > 0:
                items = []
                for item in sections:
                    items.append(item.string)
                info[key] = ' / '.join(items)
            elif len(lists) > 0:
                items = []
                for item in lists:
                    items.append(item.string)
                info[key] = ' / '.join(items)
        except:
            pass
    # Find Plot Outline/Summary:
    # Normally the tag is named "Plot Outline:" - however sometimes
    # the tag is "Plot Summary:" or just "Plot:". Search for all strings.
    imdb_result = soup.find(text='Plot Outline:')
    if not imdb_result:
        imdb_result = soup.find(text='Plot Summary:')
    if not imdb_result:
        imdb_result = soup.find(text='Plot:')
    if imdb_result:
        info['plot'] = imdb_result.next.strip()
    else:
        info['plot'] = u''
    # Find tagline - sometimes the tagline is missing.
    # Use an empty string if no tagline could be found.
    imdb_result = soup.find(text='Tagline:')
    if imdb_result:
        info['tagline'] = imdb_result.next.strip()
    else:
        info['tagline'] = u''
    rating = soup.find(text='User Rating:').findNext(text=re.compile('/10'))
    if rating:
        votes = rating.findNext('a')
        info['rating'] = rating.strip() + ' (' + votes.string.strip() + ')'
    else:
        info['rating'] = ''
    runtime = soup.find(text='Runtime:')
    if runtime and runtime.next:
        info['runtime'] = runtime.next.strip()
    else:
        info['runtime'] = ''
    # Replace special characters in the items
    for (k,v) in info.items():
        info[k] = v.strip().replace('\n',' ').replace('  ',' ').replace('&','&amp;').\
                  replace('&amp;#','&#').replace('<','&lt;').replace('>','&gt;').\
                  replace('"','&quot;')
    return info
