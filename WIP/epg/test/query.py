import time
import kaa.epg

kaa.epg.load('test.db')
print kaa.epg.get_channels()
print kaa.epg.search(time=time.time())
