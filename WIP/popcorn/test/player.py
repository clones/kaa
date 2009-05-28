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
    yield p.play()


@kaa.coroutine()
def key(code, p):
    print 'PRESS', code
    if code == 'left':
        p.seek(-10)
    elif code == 'right':
        p.seek(10)
    elif code == 'space':
        p.pause_toggle()
    elif code == 'q':
        yield p.stop()
        raise SystemExit


def status(oldpos, newpos):
    print 'Status: %f\r' % newpos,
    sys.stdout.flush()


p = kaa.popcorn2.Player()

kaa.signals['stdin_key_press_event'].connect(key, p)
p.signals['position-changed'].connect(status)
start(p)
kaa.main.run()
