import time
import kaa.epg

kaa.epg.load('test.db')
print kaa.epg.get_channels()

kaa.epg.listen()
kaa.main.run()
