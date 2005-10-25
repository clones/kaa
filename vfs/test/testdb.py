from kaa.base.db import *
from kaa.base.utils import str_to_unicode
import time
import sys

db = Database()
db.register_object_type_attrs("image",
    name = (str, ATTR_KEYWORDS | ATTR_KEYWORDS_FILENAME | ATTR_INDEXED),
    width = (int, ATTR_SEARCHABLE),
    height = (int, ATTR_SEARCHABLE),
    date =  (int, ATTR_SEARCHABLE),
    comment = (unicode, ATTR_KEYWORDS)
)

db.register_object_type_attrs("audio", 
    name = (str, ATTR_KEYWORDS | ATTR_KEYWORDS_FILENAME | ATTR_INDEXED),
    title = (unicode, ATTR_KEYWORDS),
    artist = (unicode, ATTR_KEYWORDS | ATTR_INDEXED),
    album = (unicode, ATTR_KEYWORDS),
    genre = (unicode, ATTR_SEARCHABLE),
    samplerate = (int, ATTR_SIMPLE),
    length = (int, ATTR_SIMPLE),
    bitrate = (int, ATTR_SIMPLE),
    trackno = (int, ATTR_SIMPLE)
)

db.register_object_type_attrs("dir",
    name = (str, ATTR_KEYWORDS | ATTR_KEYWORDS_FILENAME | ATTR_INDEXED),
    is_removable = (int, ATTR_SEARCHABLE)
)

dir = db.query(type="dir", name="/home/freevo/mp3")
if not dir:
    t0=time.time()
    print "* Creating (database) directory with 20000 objects"
    dir = db.add_object("dir", name="/home/freevo/mp3", foo=1)
    for i in xrange(10000):
        if i < 5000:
            comment = u"Anna's birthday, June 2003"
        else:
            comment = u"My vacation to Hawaii, December 2004"

        db.add_object("image", name="foobar%s.jpg" % i, parent=("dir", dir["id"]),
                      width=i, height=100, comment=comment)
        db.add_object("audio", name="enya%s.mp3" % i, parent=("dir", dir["id"]),
                      artist=u"Enya")

    # This tests worst-case
    db.add_object("image", name="other.jpg", parent=("dir", dir["id"]), width=100, height=100, 
                  comment=u"birthday vacation")

    print "* Creation took %.03f seconds" % (time.time()-t0)
else:
    dir = dir[0]

t0=time.time()
rows = db.query(keywords="anna", limit=100)
print "* Keyword query took %.03f seconds, %d rows" % (time.time()-t0, len(rows))

t0=time.time()
rows = db.query(keywords="birthday vacation", limit=100)
print "* Keyword query (worst case) took %.03f seconds, %d rows" % (time.time()-t0, len(rows))

t0=time.time()
db.update_object(("image", 200), comment=u"This is a test")
print "* Update object (with keyword reindex) took %.03f seconds" % (time.time()-t0)

t0=time.time()
rows = db.query_raw(parent = ("dir", dir["id"]))
print "* Query (raw) by parent took %.03f seconds" % (time.time()-t0)

t0=time.time()
rows = db.normalize_query_results(rows)
print "* Normalize results list took took %.03f seconds" % (time.time()-t0)

t0=time.time()
db.register_object_type_attrs("audio",
    [("genre", "artist")],
    comment = (unicode, ATTR_KEYWORDS)
)
print "* Modify type took %.03f seconds" % (time.time()-t0)

t0=time.time()
db.query_raw(parent = ("dir", dir["id"]), name="foobar2499.jpg")
print "* Query for single filename took %.05f seconds" % (time.time()-t0)

t0=time.time()
db.delete_object(("image", 801))
print "* Single object delete took %.05f seconds" % (time.time()-t0)

count = db._db_query("SELECT count(*) FROM words")
print "--\nWords table has %d rows" % count[0]
count = db._db_query("SELECT count(*) FROM words_map")
print "Words map table has %d rows" % count[0]

t0=time.time()
print db.delete_by_query(object=("dir", 1))
print "Mass delete", time.time()-t0
