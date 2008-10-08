import time
import sys

def scan(tuner, vbi, frequencies):
    found = []
    for freq in frequencies:
        tuner.setchannel(freq)
        time.sleep(0.5)
        vbi.reset()
        print 'scan %-5s...' % freq,
        sys.__stdout__.flush()

        if tuner.gettuner(0)['signal']:
            sys.__stdout__.flush()
            time.sleep(0.25)
            start = time.time()
            while time.time() - 3 < start:
                # scan 3 seconds for network name
                try:
                    vbi.read_sliced()
                except:
                    print 'failed to read vbi slice'

                if vbi.network:
                    print 'found "%s" (%s)' % vbi.network
                    chanid = vbi.network[0]
                    break
            else:
                print 'unkown network "%s"' % freq
                status = 'not identified'
                chanid = freq
            found.append((freq, chanid))
        else:
            print 'no channel'
    return found
