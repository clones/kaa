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
    

