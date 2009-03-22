# TODO: maybe move that into one of the bin scripts
# e.g. beacon-daemon --clear-thumbnails

import os
import sys
import kaa
import kaa.metadata

files = []
num_deleted = 0

FORCE=True

def update(progress):
    eta = int(progress.eta)
    sys.stdout.write('\r' + progress.get_progressbar(40))
    sys.stdout.write(' %s/%s' % (progress.pos, progress.max))
    sys.stdout.write(' ETA %02d:%02d' % (eta / 60, eta % 60))
    sys.stdout.flush()

    
def scan(files, progress):
    global num_deleted
    for thumbnail in files:
        progress.update()
        metadata = kaa.metadata.parse(thumbnail)
        if not metadata:
            if FORCE:
                os.unlink(thumbnail)
                num_deleted += 1
            continue
        uri = metadata['Thumb::URI']
        if not uri:
            if FORCE:
                os.unlink(thumbnail)
                num_deleted += 1
            continue
        uri = kaa.unicode_to_str(uri)
        if not uri.startswith('file://'):
            if FORCE:
                os.unlink(thumbnail)
                num_deleted += 1
            continue
        if not os.path.isfile(uri[7:]):
            os.unlink(thumbnail)
            num_deleted += 1
        
sys.stdout.write('scan thumbnail directory')
sys.stdout.flush()

for directory in ('fail/kaa', 'large', 'normal'):
    path = os.path.expanduser('~/.thumbnails/' + directory)
    if os.path.isdir(path):
        for thumbnail in os.listdir(path):
            files.append(path + '/' + thumbnail)

progress = kaa.InProgress.Progress(len(files))
progress.connect(update)
scan(files, progress)
print
print 'Checked %s thumbnails' % len(files)
print 'Deleted %s files' % num_deleted
