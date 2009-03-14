import os
import sys
import kaa.beacon
import kaa.webmetadata

tvdb = kaa.webmetadata.TVDB(os.path.expanduser("~/.beacon/tvdb"))

@kaa.coroutine()
def main():
    for name in [ a['tvdb'] for a in tvdb._db.query(type='alias') ]:
        print name
        # FIXME: the likes operator is broken in kaa.db when doing the query
        for r in (yield kaa.beacon.query(type='video', name=kaa.beacon.QExpr("like", str(name + '%')))):
            entry = tvdb.from_filename(r.filename)
            if entry.series and entry.episode:
                desc = entry.episode.data['data'].get('Overview')
                if desc:
                    print 'add description to', r.filename
                    r['description'] = desc
        print
    print 'done'
    sys.exit(0)
    
kaa.beacon.connect()
main()
kaa.main.run()
