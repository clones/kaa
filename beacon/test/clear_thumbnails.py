# TODO: maybe move that into one of the bin scripts
# e.g. beacon-daemon --clear-thumbnails

import os
import sys
import kaa
import kaa.metadata

files = []
num_deleted = 0

FORCE=True

for directory in ('fail/kaa', 'large', 'normal'):
    path = os.path.expanduser('~/.thumbnails/' + directory)
    if os.path.isdir(path):
        for thumbnail in os.listdir(path):
            files.append(path + '/' + thumbnail)

for pos, thumbnail in enumerate(files):

    n = int((pos / float(len(files))) * 50)
    sys.stdout.write("|%51s| %d / %d\r" % (("="*n + ">").ljust(51), pos, len(files)))
    sys.stdout.flush()

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
        
print
print 'Checked %s thumbnails' % len(files)
print 'Deleted %s files' % num_deleted

