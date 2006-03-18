import logging

import kaa
from kaa.epg2 import GuideServer

logging.getLogger().setLevel(logging.DEBUG)

guide = GuideServer("epg", dbfile="epgdb")
kaa.main()
