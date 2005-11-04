import os
import stat

from kaa.notifier import Timer
import kaa.metadata

def get_mtime(item):
    if not item.filename:
        print 'no filename == no mtime :('
        return 0

    mtime = 0
    if item.isdir:
        return os.stat(item.filename)[stat.ST_MTIME]

    # mtime is the the mtime for all files having the same
    # base. E.g. the mtime of foo.jpg is the sum of the
    # mtimeof foo.jpg and foo.jpg.xml or for foo.mp3 the
    # mtime is the sum of foo.mp3 and foo.jpg.

    base = os.path.splitext(item.filename)[0]

    # TODO: add overlay support

    # TODO: Make this much faster. We should cache the listdir
    # and the stat results somewhere, maybe already split by ext
    # But since this is done in background, this is not so
    # important right now.
    files = map(lambda x: item.dirname + x, os.listdir(item.dirname))
    for f in filter(lambda x: x.startswith(base), files):
        mtime += os.stat(f)[stat.ST_MTIME]
    return mtime


def parse(db, item):
    mtime = get_mtime(item)
    if not mtime:
        print 'oops, no mtime', item
        return
    if isinstance(item.data, dict) and item.data['mtime'] == mtime:
        print 'up-to-date', item
        return
    print 'scan', item
    attributes = { 'mtime': mtime }
    metadata = kaa.metadata.parse(item.filename)
    if isinstance(item.data, dict):
        type = item.data['type']
    elif metadata and metadata['media'] and \
             db._object_types.has_key(metadata['media']):
        type = metadata['media']
    elif item.isdir:
        type = 'dir'
    else:
        type = 'file'

    type_list = db._object_types[type]
    for key in type_list[1].keys():
        if metadata and metadata.has_key(key) and metadata[key] != None:
            attributes[key] = metadata[key]

    # TODO: do some more stuff here:
    # - check metadata for thumbnail or cover (audio) and use kaa.thumb to store it
    # - schedule thumbnail genereation with kaa.thumb
    # - search for covers based on the file (should be done by kaa.metadata)
    # - maybe the item is now in th db so we can't add it again

    # FIXME: the items are not updated yet, the changes are still in
    # the queue and will be added to the db on commit.

    if item.dbid:
        # update
        db.update_object(item.dbid, **attributes)
        item.data.update(attributes)
    else:
        # create
        db.add_object(type, name=item.basename, parent=item.parent.dbid, **attributes)
    return True


class Checker(object):
    def __init__(self, db, items, notify):
        self.db = db
        self.items = items
        self.max = len(items)
        self.pos = 0
        self.notify = notify
        Timer(self.check).start(0.01)

    def check(self):
        if not self.items:
            print 'commit changes'
            self.db.commit()
            self.notify('changed')
            return False
        self.pos += 1
        self.notify('progress', self.pos, self.max)
        item = self.items[0]
        self.items = self.items[1:]
        parse(self.db, item)
        return True

