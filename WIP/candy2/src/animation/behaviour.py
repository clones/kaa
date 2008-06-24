# clutter imports
import clutter

# gui imports
from kaa.candy import Color

class BehaviourColor(clutter.Behaviour):
    """
    Behaviour to change the color of an actor.
    """
    __gtype_name__ = 'BehaviourColor'

    def __init__ (self, alpha, start_color, end_color):
        clutter.Behaviour.__init__(self)
        self.set_alpha(alpha)
        self._start = start_color
        self._end = end_color

    def do_alpha_notify(self, alpha_value):
        color = []
        for pos in range(4):
            start = self._start[pos]
            diff =  self._end[pos] - start
            alpha = float(alpha_value) / clutter.MAX_ALPHA
            color.append(start + int(diff * alpha))
        for actor in self.get_actors():
            actor.set_color(Color(*color))
