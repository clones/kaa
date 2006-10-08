import os
import sys
import kaa.strutils
import kaa.metadata

verbose = False
files = []
num_deleted = 0

for directory in ('fail/kaa', 'large', 'normal'):
    path = os.path.expanduser('~/.thumbnails/' + directory)
    for thumbnail in os.listdir(path):
        files.append(path + '/' + thumbnail)

for pos, thumbnail in enumerate(files):

    n = int((pos / float(len(files))) * 50)
    sys.stdout.write("|%51s| %d / %d\r" % (("="*n + ">").ljust(51), pos, len(files)))
    sys.stdout.flush()

    metadata = kaa.metadata.parse(thumbnail)
    if not metadata:
        print '\nbad thumbnail: %s' % thumbnail
        continue
    uri = metadata['Thumb::URI']
    if not uri:
        print '\nbad thumbnail: %s' % thumbnail
        continue
    uri = kaa.strutils.unicode_to_str(uri)
    if not uri.startswith('file://'):
        print '\nbad uri %s in thumbnail: %s' % (uri, thumbnail)
        continue
    if not os.path.isfile(uri[7:]):
        if verbose:
            print '\ndelete thumbnail for', uri[7:]
        os.unlink(thumbnail)
        num_deleted += 1
        
print
print 'Checked %s thumbnails' % len(files)
print 'Deleted %s files' % num_deleted

