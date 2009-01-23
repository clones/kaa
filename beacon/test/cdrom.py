import kaa
import kaa.beacon

def new_device(media):
    print 'new', media
    kaa.OneShotTimer(media.eject).start(5)
    
def lost_device(media):
    print 'lost', media

kaa.beacon.connect().wait()
kaa.beacon.signals['media.add'].connect(new_device)
kaa.beacon.signals['media.remove'].connect(lost_device)
kaa.main.run()
