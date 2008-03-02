# behaviour example from clutter distribution with some kaa magic

import kaa
import time
import sys
import clutter
import gobject

class BehaviourRotate (clutter.Behaviour):
    __gtype_name__ = 'BehaviourRotate'
    def __init__ (self, alpha=None):
        clutter.Behaviour.__init__(self)
	self.set_alpha(alpha)
	self.angle_start = 0.0
	self.angle_end = 359.0

    def do_alpha_notify (self, alpha_value):
        angle = alpha_value * (self.angle_end - self.angle_start) \
		/ clutter.MAX_ALPHA

        for actor in self.get_actors():
            actor.set_rotation(clutter.Z_AXIS, angle, actor.get_x() - 100,
                               actor.get_y() - 100, 0)


@kaa.threaded(kaa.MAINTHREAD)
def key_press(stages, event):
    print 'exit'
    sys.exit(0)
    
@kaa.threaded(kaa.GOBJECT)
def do_stuff ():
    # clutter is not thread safe. They claim they are, but they are
    # not. So better change clutter stuff in the GOBJECT thread.
    stage = clutter.Stage()
    stage.set_size(800, 600)
    stage.set_color(clutter.Color(0xcc, 0xcc, 0xcc, 0xff))
    stage.connect('key-press-event', key_press)

    rect = clutter.Rectangle()
    rect.set_position(0, 0)
    rect.set_size(150, 150)
    rect.set_color(clutter.Color(0x33, 0x22, 0x22, 0xff))
    rect.set_border_color(clutter.color_parse('white'))
    rect.set_border_width(15)
    rect.show()

    knots = ( \
            (   0,   0 ),   \
            ( 300,   0 ),   \
            ( 300, 300 ),   \
            (   0, 300 ),   \
    )

    timeline = clutter.Timeline(fps=60, duration=3000)
    timeline.set_loop(True)
    alpha = clutter.Alpha(timeline, clutter.sine_func)

    o_behaviour = clutter.BehaviourOpacity(alpha=alpha, opacity_start=0x33, opacity_end=255)
    o_behaviour.apply(rect)

    p_behaviour = clutter.BehaviourPath(alpha=alpha, knots=knots)
    p_behaviour.append_knots((0, 0))
    p_behaviour.apply(rect)

    r_behaviour = BehaviourRotate(alpha)
    r_behaviour.apply(rect)

    stage.add(rect)
    stage.show()

    timeline.start()
    # return all animation objects to prevent the gc from deleting them
    return o_behaviour, p_behaviour, r_behaviour


@kaa.threaded(kaa.GOBJECT)
def clutter_init():
    clutter.threads_init()
    clutter.init()

def block():
    # a long running function that should not stop the animations
    import time
    print 'blocking'
    time.sleep(2)

if 1:
    # force generic nf here so gtk won't be auto-selected
    # because of clutter gtk import
    kaa.main.select_notifier('generic')
    kaa.gobject_set_threaded()
if 0:
    # this cause the animation to block in block()
    kaa.main.select_notifier('gtk')

# init clutter in GOBJECT thread
clutter_init()
# remember clutter objects from do_stuff or the gc will delete
# the objects and the animations won't work.
references_to_prevent_gc = do_stuff()
kaa.OneShotTimer(block).start(1.5)

kaa.main.run()
print 'done'
