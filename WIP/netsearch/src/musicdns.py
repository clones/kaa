import os
import ofa
import urllib
import kaa
import kaa.notifier
import libxml2
import popen2

try:
    from musicbrainz2.webservice import TrackFilter, Query
    musicbrainz = True
except:
    musicbrainz = False
    

class MusicDNS(object):
    def __init__(self, cid, cvr):
        self.cid = cid
        self.cvr = cvr

        self.signals = { 'completed': kaa.notifier.Signal(),
                         'exception': kaa.notifier.Signal() }
        
    def search(self, filename):
        sig = self._detect_thread(filename)
        sig.connect(self.signals['completed'].emit)
        sig.exception_handler.connect(self.signals['exception'].emit)


    @kaa.notifier.execute_in_thread('netsearch')
    def _detect_thread(self, filename):
        wav = '%s/musicdns.wav' % kaa.TEMP
        if os.path.isfile(wav):
            os.unlink(wav)
        child = popen2.Popen4(['mplayer', '-ao', 'pcm:file=%s' % wav, filename])
        while child.fromchild.read():
            pass
        child.wait()
        if not os.path.isfile(wav):
            raise RuntimeError('converting to wav failed')
        fingerprint, ms = ofa.parse(wav)
        if not fingerprint:
            raise RuntimeError('no fingerprint')
        params = urllib.urlencode(dict(
            cid=self.cid, cvr=self.cvr, fpt=fingerprint, rmd=1, brt=0,
            fmt='wav', dur=ms, art='unknown', ttl='unknown',
            alb='unknown', tnm=0, gnr='unknown', yrr=0))
        f = urllib.urlopen("http://ofa.musicdns.org/ofa/1/track", params)
        data = f.read()
        f.close()
        title = name = puid = ''
        doc = libxml2.parseDoc(data)
        for d in doc.children:
            if d.name == 'title':
                title = d.content
                continue
            if d.name == 'name':
                name = d.content
                continue
            if d.name == 'puid':
                puid = d.prop('id')
                continue
        doc.free();

        if not puid:
            raise RuntimeError('no puid')

        results = []
        if musicbrainz:
            for r in Query().getTracks(TrackFilter(puid=puid)):
                # filter out possible bad results (duration += 20 sec)
                # adding duration to TrackFilter doesn't help :(
                if r.track.duration and \
                       (r.track.duration - 20000 > ms or \
                        r.track.duration + 20000 < ms):
                    continue
                for rel in r.track.releases:
                    results.append((
                        r.track.title,                  # title
                        r.track.artist.name,            # artist
                        ms,                             # length
                        rel.title,                      # album
                        rel.asin,                       # ASIN
                        ))

        if title and name and not results:
            results.append((title, name, ms, None, None))

        return puid, results
