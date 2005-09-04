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

print kaa.vfs.query(keywords='wir helden')

def distinct_query(var, type):
    # TODO: add support for DISTINCT queries to the db
    result = []
    for r in kaa.vfs._db._db_query('SELECT DISTINCT %s from objects_%s' % (var, type)):
        if r[0]:
            result.append(r[0])
    result.sort()
    return result

if 0:
    for a in distinct_query('album', 'audio'):
        print a.encode(locale.getpreferredencoding())

if 0:
    for a in distinct_query('artist', 'audio'):
        print a.encode(locale.getpreferredencoding())

kaa.vfs.commit()
