import time

from kaa.vfs.mediadb import *

dirs_to_test = ('/home/dmeyer/mp3', '/home/dmeyer/video')

print 'opendb'
db = MediaDB()

for dir in dirs_to_test:

    t1 = time.time()
    listing = db.listdir(dir)
    print 'List Time:', time.time() - t1
    print listing

    t1 = time.time()
    listing.update()
    print 'Update Time:', time.time() - t1
    print listing


print '*****************'
i = db.file('/home/dmeyer/video/serenity_international.mov')
print 'Data', i.items()

if i.has_key('foo'):
    i['foo'] = None
else:
    i['foo'] = 1
i._update()

print 'get info again from the db'
i = db.file('/home/dmeyer/video/serenity_international.mov')
print 'Data', i.items()

db.commit()
