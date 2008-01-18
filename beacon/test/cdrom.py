import kaa
import kaa.beacon

kaa.beacon.connect()
kaa.beacon.add_mountpoint('cdrom', '/dev/dvd', '/mnt/dvd')
kaa.beacon.add_mountpoint('cdrom', '/dev/cdrom', '/mnt/cdrom')

kaa.main.run()
