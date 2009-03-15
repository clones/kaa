import os
import sys
import kaa.webmetadata
import kaa.beacon

@kaa.coroutine()
def main():
    print 'check for missing tvdb mapping'
    print '------------------------------'
    tvdb = kaa.webmetadata.TVDB(os.path.expanduser("~/.beacon/tvdb"))
    missing = []
    for alias in (yield kaa.beacon.query(type='video', attr='tvdb_alias')):
        if alias in tvdb.aliases:
            continue
        print 'Missing mapping for "%s"' % alias
        print 'Files:'
        for item in (yield kaa.beacon.query(type='video', tvdb_alias=alias)):
            print ' ', item.filename
        results = yield tvdb.search_series(alias)
        if len(results) == 0:
            print 'No query results'
        elif len(results) == 1:
            data = results[0]
            print 'Auto-mapping to'
            print '  id=%s name="%s" year="%s"' % (data['id'], data['SeriesName'], data.get('FirstAired'))
            yield tvdb.match_series(alias, int(data['id']))
        else:
            print 'Query'
            for data in results:
                print '  id=%s name="%s" year="%s"' % (data['id'], data['SeriesName'], data.get('FirstAired'))
        print
        print
    sys.exit(0)

main()
kaa.main.run()
