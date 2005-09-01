import time, sys, os, locale
from kaa.vfs import *
from kaa.base.utils import str_to_unicode
from kaa import metadata

AUDIO_PATH = u"/data/mp3"
#AUDIO_PATH = "/data/mp3/Enya - Watermark"

db = Database("testdb2.sqlite")
db.register_object_type_attrs("audio", (
    ("title", unicode, ATTR_KEYWORDS),
    ("artist", unicode, ATTR_KEYWORDS | ATTR_INDEXED),
    ("album", unicode, ATTR_KEYWORDS),
    ("genre", unicode, ATTR_INDEXED),
    ("samplerate", int, ATTR_SIMPLE),
    ("length", int, ATTR_SIMPLE),
    ("bitrate", int, ATTR_SIMPLE),
    ("trackno", int, ATTR_SIMPLE))
)


def index(dir):
    dir_object = db.add_object(("dir", str_to_unicode(dir)))
    for entry in os.listdir(dir):
        filepath = os.path.abspath(os.path.join(dir,entry))
        dirname, filename = os.path.split(filepath)
        filename_noext, ext = os.path.splitext(filename)

        if os.path.isdir(filepath):
            index(filepath)
            continue

        if ext not in (".mp3", ".ogg"):
            continue

        md = metadata.parse(filepath)
        sys.stdout.write(" " * 79 + "\r")
        if not md:
            print "FAILED:", filepath
            continue

        sys.stdout.write("Processing: %s\r" % filename)
        sys.stdout.flush()

        db.add_object(("audio", str_to_unicode(filename)), parent=("dir", dir_object["id"]),
                title=md.get("title"),
                artist=md.get("artist"), album=md.get("album"), genre=md.get("genre"),
                samplerate=md.get("samplerate"), length=md.get("length"), 
                bitrate=md.get("bitrate"), trackno=md.get("trackno"))

dir = db.query_normalized(type="dir", name=AUDIO_PATH)
if not dir:
    t0 = time.time()
    index(AUDIO_PATH)
    count = db._db_query_row("SELECT count(*) from objects_audio")
    print "Indexed %d files in %.02f seconds." % (count[0], time.time()-t0)

print "Type some query words, CTRL-C quits:"
while 1:
    q = str_to_unicode(sys.stdin.readline())
    kwargs = {}
    kwargs["limit"] = 20
    for term in q.split():
        if term.find("=") != -1:
            key, val = term.split("=")
            if val.isdigit():
                val = int(val)
            kwargs[str(key)] = val
        else:
            if "keywords" not in kwargs:
                kwargs["keywords"] = term
            else:
                kwargs["keywords"] += " " + term

    t0=time.time()
    rows = db.query_normalized(**kwargs)
    print "* Keyword query took %.03f seconds, %d rows" % (time.time()-t0, len(rows))
    for row in rows:
        if row["type"] == "audio":
            print "\t%s (Artist: %s, Album: %s)" % (row["name"], row["artist"], row["album"])
        else:
            print "\t%s (type=%s)" % (row["name"], row["type"])
