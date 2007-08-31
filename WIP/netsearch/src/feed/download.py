import os
import stat
import urllib
import urllib2
import kaa.notifier

def fetch_HTTP(url, filename):
    """
    Fetch HTTP URL.
    """
    def download(url, filename, status):
        src = urllib2.urlopen(url)
        length = int(src.info().get('Content-Length', 0))
        if os.path.isfile(filename) and os.stat(filename)[stat.ST_SIZE] == length:
            return True
        tmpname = os.path.join(os.path.dirname(filename),
                               '.' + os.path.basename(filename))
        dst = open(tmpname, 'w')
        status.set(0, length)
        while True:
            data = src.read(1024)
            if len(data) == 0:
                src.close()
                dst.close()
                os.rename(tmpname, filename)
                return True
            status.update(len(data))
            dst.write(data)

    if url.find(' ') > 0:
        # stupid url encoding in url
        url = url[:8+url[8:].find('/')] + \
              urllib.quote(url[8+url[8:].find('/'):])
    s = kaa.notifier.Progress()
    t = kaa.notifier.Thread(download, url, filename, s)
    t.wait_on_exit(False)
    async = t.start()
    async.set_status(s)
    return async


def fetch(url, filename):
    """
    Generic fetch function.
    """
    if url.startswith('http://') or url.startswith('https://'):
        return fetch_HTTP(url, filename)
    raise RuntimeError('unable to fetch %s' % url)
