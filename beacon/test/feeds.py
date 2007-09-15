import sys
import kaa.notifier
import kaa.beacon

kaa.beacon.connect()

if len(sys.argv) > 1:
    if sys.argv[1] in ('--update', '-u'):
        if len(sys.argv) > 2:
            def update(feeds, id):
                for f in feeds:
                    if f.get('id') == id:
                        f.update().connect(sys.exit)
            kaa.beacon.list_feeds().connect(update, int(sys.argv[2]))
        else:
            kaa.beacon.update_feeds().connect(sys.exit)

    elif sys.argv[1] in ('--list', '-l'):
        def show(feeds):
            for f in feeds:
                print f
            sys.exit(0)
        kaa.beacon.list_feeds().connect(show)

    elif sys.argv[1] in ('--add', '-a') and len(sys.argv) > 3:
        url = sys.argv[2]
        destdir = sys.argv[3]
        if len(sys.argv) > 4:
            if sys.argv[4].lower() in ('true', 'yes'):
                download = True
            elif sys.argv[4].lower() in ('false', 'no'):
                download = False
            num = int(sys.argv[5])
            if sys.argv[6].lower() in ('true', 'yes'):
                keep = True
            elif sys.argv[6].lower() in ('false', 'no'):
                keep = False
            kaa.beacon.add_feed(url, destdir, download, num, keep).connect(sys.exit)
        else:
            kaa.beacon.add_feed(url, destdir).connect(sys.exit)

    elif sys.argv[1] in ('--remove', '-r') and len(sys.argv) > 2:
        def remove(feeds, id):
            for f in feeds:
                if f.get('id') == id:
                    f.remove().connect(sys.exit)
        kaa.beacon.list_feeds().connect(remove, int(sys.argv[2]))
        
    else:
        print 'help'
        sys.exit(0)
        
    kaa.notifier.loop()
    sys.exit(0)

print 'help'
# Add example
# python test/feeds.py -a http://www.radiobremen.de/podcast/bestof/ \
#      /local/podcast False 2 False
