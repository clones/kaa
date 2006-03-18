import logging

import kaa
from kaa.epg import GuideServer

logging.getLogger().setLevel(logging.DEBUG)

guide = GuideServer("epg", dbfile="epgdb")
kaa.main()
