import kaa.popcorn2
from kaa.popcorn2 import config
import kaa.input.stdin
import sys
import logging
import time

logging.getLogger('popcorn').setLevel(logging.DEBUG)

@kaa.coroutine()
def start(p):
    yield p.open(sys.argv[1])
    p.stream.fullscreen = True
    yield p.play()


@kaa.coroutine()
def key(code, p):
    print 'PRESS', code
    if code in ('left', 'right', 'up', 'down'):
        p.seek({'left': -10, 'right': 10, 'up': 60, 'down': -60}.get(code))
    elif code == 'space':
        p.pause_toggle()
    elif code == 'q':
        yield p.stop()
        raise SystemExit
    elif code == 'a':
        p.stream.audio_delay += 0.1
        print 'Audio delay is', p.stream.audio_delay
    elif code == 'A':
        p.stream.audio_delay -= 0.1
        print 'Audio delay is', p.stream.audio_delay
    elif code == 'D':
        p.stream.deinterlace = not p.stream.deinterlace
        print 'Deinterlacing is', p.stream.deinterlace


def status(oldpos, newpos):
    print 'Status: %f\r' % newpos,
    sys.stdout.flush()


#config.video.driver = 'vdpau'
p = kaa.popcorn2.Player()
kaa.signals['stdin_key_press_event'].connect(key, p)
p.signals['position-changed'].connect(status)
start(p)
kaa.main.run()
