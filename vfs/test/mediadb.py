import time

from kaa.vfs.mediadb import *

dirs_to_test = ('/home/dmeyer/mp3', '/home/dmeyer/video')

print 'opendb'
db = MediaDB()

for dir in dirs_to_test:
    t1 = time.time()
    db.scan_dir(dir)
    print 'Scan Time:', time.time() - t1
    t1 = time.time()
    fir, files = db.listdir(dir)
    print 'List Time:', time.time() - t1
    if len(files) < 10:
        print files
    else:
        print len(files), 'results'
    print
