import sys
from kaa.base.db import Database

parents = []
db = Database(sys.argv[1] + '/db')
for d in db.query(type='dir'):
    print 'directory %s (id=%s)' % (d['name'], d['id'])
    parents.append((d['type'], d['id']))
    for f in db.query(parent=(d['type'], d['id'])):
        print ' content %s %s (id=%s)' % (f['type'], f['name'], f['id'])
        
print
print 'orphans'
for type in db._object_types.keys():
    for f in db.query(type=type):
        if not f['parent_type'] or not f['parent'] in parents:
            print f
