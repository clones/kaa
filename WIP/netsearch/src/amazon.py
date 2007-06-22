__all__ = [ 'search' ]

import os
import logging
import urllib
import kaa.xmlutils
import kaa.imlib2

log = logging.getLogger('netsearch')

_supportedLocales = {
        "us" : (None, "xml.amazon.com"),
        "uk" : ("uk", "xml-eu.amazon.com"),
        "de" : ("de", "xml-eu.amazon.com"),
        "jp" : ("jp", "xml.amazon.com")
    }

PRODUCT_VIDEO = 'dvd'
PRODUCT_AUDIO = 'audio'

class AmazonXML(kaa.xmlutils.SaxTreeHandler):

    def __init__(self, f):
        kaa.xmlutils.SaxTreeHandler.__init__(self, 'Details')
        self.results = []
        self.parse(f)

    def handle(self, node):
        entry = {}
        # parse everything we can get
        for child in node.children:
            if not child.children:
                entry[child.name] = child.content
            elif child.name in ('Artists', 'Lists', 'Tracks', 'Features'):
                entry[child.name] = [ c.content for c in child.children ]
        entry['url'] = node.getattr('url')
        self.results.append(entry)
        # normalize key names
        entry['title'] = entry.get('ProductName')
        # grab image
        for imageurl in 'ImageUrlLarge', 'ImageUrlMedium', 'ImageUrlSmall':
            if not entry.get(imageurl):
                continue
            try:
                m = urllib.urlopen(entry.get(imageurl))
            except (KeyboardInterrupt, SystemExit), e:
                raise e
            except:
                continue
            if m.info()['Content-Length'] == '807':
                m.close()
                continue
            entry['image'] = kaa.imlib2.open_from_memory(m.read())
            m.close()
            break


def search(search_type, keyword, product_line, locale='us'):
    """
    Search Amazon for video or audio metadata.
    """
    if not os.path.isfile(os.path.expanduser('~/.amazonkey')):
        log.error('unable to get amazon licence key from ~/.amazonkey')
        return []
    license_key = open(os.path.expanduser('~/.amazonkey')).read().strip()
    url = "http://" + _supportedLocales[locale][1] + \
          "/onca/xml3?f=xml&t=webservices-20" + \
          "&dev-t=%s&type=%s" % (license_key, 'heavy')
    if product_line:
          url += "&mode=%s" % product_line
    url += "&%s=%s" % (search_type, urllib.quote(keyword))
    if _supportedLocales[locale][0]:
        url += "&locale=%s" % _supportedLocales[locale][0]
    log.info('read %s', url)
    try:
        return AmazonXML(urllib.urlopen(url)).results
    except (KeyboardInterrupt, SystemExit), e:
        raise e
    except:
        log.exception('amazon')
        return []

if __name__ == "__main__":
    print search('UpcSearch', '085393162320', PRODUCT_VIDEO)
    print search('KeywordSearch', 'west wing', PRODUCT_VIDEO)
