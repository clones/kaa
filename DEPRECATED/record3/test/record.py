import kaa.notifier
import kaa.record3

kaa.notifier.init('gtk')

dvb = kaa.record3.get_device('dvb0')
dvb.read_channels_conf('/home/dmeyer/channels.conf')
print dvb.get_channels()

r1 = kaa.record3.Recording(dvb, 'Das Erste', 'ARD.ts')
r2 = kaa.record3.Recording(dvb, 'Das Erste', 'ARD2.ts')

kaa.notifier.OneShotTimer(r1.start).start(0)
kaa.notifier.OneShotTimer(r2.start).start(2)
# kaa.notifier.OneShotTimer(r3.start, dvb).start(10)
kaa.notifier.OneShotTimer(r1.stop).start(5)
kaa.notifier.OneShotTimer(r2.stop).start(7)
# kaa.notifier.OneShotTimer(r3.stop).start(20)
kaa.notifier.OneShotTimer(kaa.notifier.shutdown).start(15)

kaa.notifier.loop()
