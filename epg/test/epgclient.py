# Test EPG client.  EPG server must be running.
#
# With no arguments, this will query the EPG server for all programs currently
# running.  With arguments, this will query all programs that match against 
# the keywords supplied as arguments.

import os, time, sys, textwrap
import kaa
from kaa.epg2 import GuideClient

def update_progress(cur, total):
    n = 0
    if total > 0:
        n = int((cur / float(total)) * 50)
    sys.stdout.write("|%51s| %d / %d\r" % (("="*n + ">").ljust(51), cur, total))
    sys.stdout.flush()
    if cur == total:
        print

guide = GuideClient("epg")
guide.signals["update_progress"].connect(update_progress)

# Initial import
if guide.get_num_programs() == 0:
    # update() is asynchronous so we enter kaa.main() and exit it
    # once the update is finished.
    guide.signals["updated"].connect(sys.exit)

    # xmltv backend: specify path to XML file:
    guide.update("xmltv", sys.argv[1])

    # zap2it backend, specify username/passwd and optional start/stop time (GMT)
    # guide.update("zap2it", username="uname", passwd="passwd")
    kaa.main()

    print 'done'
    sys.exit(0)
    
t0 = time.time()
if len(sys.argv) > 1:
    keywords = " ".join(sys.argv[1:])
    print "Results for '%s':" % keywords
    programs = guide.search(keywords = keywords)
    # Sort by start time
    programs.sort(lambda a, b: cmp(a.start, b.start))
else:
    print "All programs currently playing:"
    programs = guide.search(time = (time.time(), time.time()+7200))
    # Sort by channel
    programs.sort(lambda a, b: cmp(a.channel.channel, b.channel.channel))
t1 = time.time()

for program in programs:
    start_time = time.strftime("%a %H:%M", time.localtime(program.start))
    print "  %s (%s): %s" % (program.channel.channel, start_time, program.title.encode('latin-1'))
    if program.desc:
        print "\t* " + "\n\t  ".join(textwrap.wrap(program.desc.encode('latin-1'), 60))
print "- Queried %d programs; %s results; %.04f seconds" % \
      (guide.get_num_programs(), len(programs), t1-t0)
