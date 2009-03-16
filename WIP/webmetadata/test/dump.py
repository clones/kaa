import os
import sys
import kaa
import kaa.webmetadata.tvdb

@kaa.coroutine()
def main():
    tvdb = kaa.webmetadata.tvdb.TVDB(os.path.expanduser("~/.beacon/tvdb"))
    f = tvdb.from_filename(sys.argv[1])
    print f.series.data
    print
    print f.episode.data
    print
    print f.series.banner
    print 
    print 'Fanart'
    for banner in f.series.fanart:
        print banner
    print
    print 'Poster'
    for banner in f.series.poster:
        print banner
    print
    print 'Series'
    for banner in f.series.banner:
        print banner
    print
    print 'Season'
    for banner in f.season.banner:
        print banner
    print
    sys.exit(0)

main()
kaa.main.run()
