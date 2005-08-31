from kaa.vfs import *
import time
import sys

db = Database()
db.register_object_type_attrs("image", (
    ("width", int, ATTR_SEARCHABLE),
    ("height", int, ATTR_SEARCHABLE),
    ("date", int, ATTR_SEARCHABLE),
    ("comment", str, ATTR_KEYWORDS))
)

db.register_object_type_attrs("audio", (
    ("title", str, ATTR_KEYWORDS),
    ("artist", str, ATTR_KEYWORDS | ATTR_INDEXED),
    ("album", str, ATTR_KEYWORDS),
    ("genre", str, ATTR_INDEXED),
    ("samplerate", int, ATTR_SIMPLE),
    ("length", int, ATTR_SIMPLE),
    ("bitrate", int, ATTR_SIMPLE),
    ("trackno", int, ATTR_SIMPLE))
)

db.register_object_type_attrs("dir", (
    ("is_removable", int, ATTR_SEARCHABLE),)
)

dir = db.query_normalized(type="dir", name="/home/freevo/mp3")
if not dir:
    t0=time.time()
    print "* Creating (database) directory with 7500 objects"
    dir = db.add_object(("dir", "/home/freevo/mp3"), foo=1)
    for i in xrange(2500):
        if i < 1000:
            comment = "Anna's birthday, June 2003"
        elif i < 1700:
            comment = "My vacation to Hawaii, December 2004"
        else:
            comment = "Trip to Finland, August 2005"

        db.add_object(("image", "foobar%s.jpg" % i), parent=("dir", dir["id"]), width=i, height=100, comment=comment)
        db.add_object(("audio", "enya%s.mp3" % i), parent=("dir", dir["id"]), artist="Enya")
        db.add_object(("audio", "yanni%s.mp3" % i), parent=("dir", dir["id"]), artist="Yanni")
    db.update_object(("dir", dir["id"]), name = "/home/freevo/mp3", is_removable = False)
    print db.query_normalized(type="dir", name="/home/freevo/mp3")
    for i in xrange(2500):
        db.add_object(("dir", "zot%d" % i), parent = ("dir", dir["id"]))

    print "* Creation took %.03f seconds" % (time.time()-t0)
else:
    dir = dir[0]

t0=time.time()
rows = db.query_normalized(keywords="anna", limit=100)
print "* Keyword query took %.03f seconds, %d rows" % (time.time()-t0, len(rows))

t0=time.time()
rows = db.query_normalized(keywords="anna vacation", limit=100)
print "* Keyword query (miss) took %.03f seconds, %d rows" % (time.time()-t0, len(rows))

t0=time.time()
db.update_object(("image", 2000), comment="This is a test")
print "* Update object (with keyword reindex) took %.03f seconds" % (time.time()-t0)

t0=time.time()
rows = db.query(parent = ("dir", dir["id"]))
print "* Query by parent took %.03f seconds" % (time.time()-t0)

t0=time.time()
files = db.list_query_results_names(rows)
print "* Simple sorted file list took %.03f seconds, %d rows" % (time.time()-t0, len(files))

t0=time.time()
rows = db.normalize_query_results(rows)
print "* Normalize results list took took %.03f seconds" % (time.time()-t0)

t0=time.time()
db.register_object_type_attrs("audio", (
    ("comment", str, ATTR_KEYWORDS),)
)
print "* Modify type took %.03f seconds" % (time.time()-t0)

t0=time.time()
db.query(parent = ("dir", dir["id"]), name="zot2499")
print "* Query for single filename took %.05f seconds" % (time.time()-t0)

t0=time.time()
db.delete_object(("image", 801))
print "* Single object delete took %.05f seconds" % (time.time()-t0)

count = db._db_query("SELECT count(*) FROM words")
print "--\nWords table has %d rows" % count[0]
count = db._db_query("SELECT count(*) FROM words_map")
print "Words map table has %d rows" % count[0]
