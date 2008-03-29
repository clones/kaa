import sys
import kaa
import dvb

@kaa.coroutine()
def scan(device, tuning_data):
    channels = []
    for t in tuning_data:
        try:
            yield device.tune(t)
        except dvb.TuneExeception, e:
            print 'failed'
            continue
        yield kaa.InProgressSignals(device.signals, 'channels')
        print 'found:', ', '.join([c[0] for c in device.channels])
        channels.append((t, device.channels))
    yield channels

def read_tuning_data(filename):
    tuning_data = []
    for line in open(filename).readlines():
        if line.startswith('#'):
            continue
        freq, bandwidth, hq, lq, mod, trans, guard, hierarchy = line.strip().split()[1:]
        if mod.startswith('QAM'):
            mod = 'QAM ' + mod[3:]
        tuning_data.append({
            "frequency": int(freq),
            "bandwidth": bandwidth[0],
            "code-rate-hp": hq,
            "code-rate-lp": lq,
            "modulation": mod,
            "trans-mode": trans,
            "guard": guard.split("/")[1],
            "hierarchy": hierarchy
        })
    return tuning_data

@kaa.coroutine()
def scan_region(device, filename):
    channels = yield scan(device, read_tuning_data(filename))
    print 'SCANNING COMPLETE'
    for t, c in channels:
        for name, sid in c:
            print name, t['frequency'], t['bandwidth'], t['code-rate-hp'], \
                  t['code-rate-lp'], t['modulation'], t['trans-mode'], \
                  t['guard'], t['hierarchy'], sid
    sys.exit(0)

kaa.main.select_notifier('generic')
kaa.gobject_set_threaded()

scanfile = '/home/dmeyer/src/dvb-apps/util/scan/dvb-t/de-Bremen'
scan_region(dvb.DVB(adapter=0, frontend=0), scanfile)

kaa.main.run()
