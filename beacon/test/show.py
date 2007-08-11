import sys
import kaa.beacon

kaa.beacon.connect()
file = kaa.beacon.get(sys.argv[1])
for key in file.keys():
	print key, file[key]
