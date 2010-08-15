import kaa.popcorn
from kaa.popcorn import config
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
    if code in ('left', 'right', 'up', 'down'):
        pos = yield p.seek({'left': -10, 'right': 10, 'up': 60, 'down': -60}.get(code))
        print 'Seeked:', pos
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
    elif code == 'f':
        p.window.set_fullscreen(not p.window.get_fullscreen())
    elif code == 'r':
        p.window.resize(1024, 768)
    elif code == 'p':
        yield start(p)


def status(oldpos, newpos):
    print 'Status: %f\r' % newpos,
    sys.stdout.flush()


config.save('popcorn.conf')
p = kaa.popcorn.Player()
#p.window = kaa.popcorn.PlayerIndependentWindow()
#p.window.fullscreen = False

# Various things we can test before starting movie.
config.video.vdpau.enabled = True
# print 'WINDOW ID: 0x%x' % p.window.id
# p.window.set_fullscreen()
# p.window = None
# p.config.video.vdpau.enabled = False
# p.config.video.deinterlacing.method = 'best'
# p.config.video.vdpau.formats += ', vc1'

kaa.signals['stdin_key_press_event'].connect(key, p)
p.signals['position-changed'].connect(status)
start(p)
kaa.main.run()
