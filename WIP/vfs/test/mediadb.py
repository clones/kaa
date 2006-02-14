import time
import locale

import kaa.vfs

dirs_to_test = ('/home/dmeyer/mp3', '/home/dmeyer/video')

print 'opendb'

kaa.vfs.connect('vfs-test')

def index(dir):
    print dir
    listing = dir.list()
    listing.update()
    for l in listing:
        if l.isdir():
            index(l)
    
for dir in dirs_to_test:

    t1 = time.time()
    listing = kaa.vfs.listdir(dir)
    print 'List Time:', time.time() - t1
    print listing

    t1 = time.time()
    listing.update()
    print 'Update Time:', time.time() - t1
    print listing

    if 0:
        for l in listing:
            if l.isdir():
                index(l)
        
print '*****************'
i = kaa.vfs.file('/home/dmeyer/video/serenity_international.mov')
print 'Data', i.items()

if i.has_key('foo'):
    i['foo'] = None
else:
    i['foo'] = 1
i._update()

print 'get info again from the db'
i = kaa.vfs.file('/home/dmeyer/video/serenity_international.mov')
print 'Data', i.items()

t1 = time.time()
listing = kaa.vfs.query(keywords='wir helden')
print 'Query Time:', time.time() - t1

if 0:
    for l in listing:
        print l['url']


t1 = time.time()
listing = kaa.vfs.query(type='audio', attrs=['album'], distinct=True)
print 'Query Time (album):', time.time() - t1

if 0:
    for r in listing:
        print r.encode(locale.getpreferredencoding())



t1 = time.time()
listing = kaa.vfs.query(type='audio', attrs=['artist'], distinct=True)
print 'Query Time (artist):', time.time() - t1

if 0:
    for r in listing:
        print r.encode(locale.getpreferredencoding())


kaa.vfs.commit()
