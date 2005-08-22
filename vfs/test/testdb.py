from kaa.vfs import *
import time

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

db.register_object_type_attrs("audio", (
    ("comment", str, ATTR_KEYWORDS),)
)

db.register_object_type_attrs("dir", (
    ("is_removable", int, ATTR_SIMPLE),)
)

dir = db.query_normalized(type="dir", name="/home/freevo/mp3")
if not dir:
    t0=time.time()
    print "Creating (database) directory with 5000 files"
    dir = db.add_object(("dir", "/home/freevo/mp3"))
    for i in xrange(2500):
        db.add_object(("image", "foobar%s.jpg" % i), parent=("dir", dir["id"]), width=100, height=100, frobate="asdf")
        db.add_object(("audio", "foobar%s.mp3" % i), parent=("dir", dir["id"]), artist="Enya")
    db.update_object(("dir", dir["id"]), name = "/home/freevo/mp3", is_removable = False)
    print "Creation took %.03f seconds" % (time.time()-t0)
else:
    dir = dir[0]

t0=time.time()
rows = db.query(parent = ("dir", dir["id"]))
print "Query took %.03f seconds" % (time.time()-t0)

t0=time.time()
files = db.list_query_results_names(rows)
print "Simple sorted file list took %.03f seconds, %d rows" % (time.time()-t0, len(files))

t0=time.time()
rows = db.normalize_query_results(rows)
print "Normalize results list took took %.03f seconds" % (time.time()-t0)

