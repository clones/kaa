# python imports
import logging

# kaa imports
import kaa
import kaa.candy

import clutter

from behaviour import BehaviourColor


# get logging object
log = logging.getLogger('kaa.candy')

# frames per second (hard-coded)
FPS = 25

class XMLDict(dict):
    """
    XML parser dict helper class.
    """
    def update(self, **kwargs):
        super(XMLDict, self).update(**kwargs)
        return self

class Template(object):
    """
    Template to create an animation on demand. All XML parser will create such an
    object to parse everything during theme parsing.
    """
    def __init__(self, style, cls, kwargs):
        self.style = style
        self._cls = cls
        self._kwargs = kwargs

    def __call__(self, widget):
        """
        Create the animation bound to the given widget.
        """
        return self._cls(widget, **self._kwargs)

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the XML element for parameter and create a Template.
        """
        animation = kaa.candy.xmlparser.get_class(element.node, element.style)
        if not animation:
            return None
        return cls(element.style, animation, animation.candyxml_parse(element))


class Animation(kaa.InProgress):
    """
    Base animation class.
    """

    __template__ = Template
    candyxml_name = 'animation'

    running = []

    def __init__(self, secs):
        super(Animation, self).__init__()
        timeline = clutter.Timeline(int(float(secs) * FPS), FPS)
        timeline.set_loop(False)
        # FIXME: do not hardcode alpha function
        self.alpha = clutter.Alpha(timeline, clutter.ramp_inc_func)
        self._refs = None

    def start(self, *refs):
        """
        Start the animation.
        """
        # print refs[0].get_alpha().get_timeline()
        self.running.append(self)
        # store references or the animation won't run
        self._refs = refs
        timeline = self.alpha.get_timeline()
        timeline.rewind()
        timeline.start()
        timeline.connect('completed', self.finish)
        self.alpha = None

    def finish(self, result):
        """
        Callback when the animation is finished.
        """
        self.running.remove(self)
        # run callback
        # deleted references for gc
        for behaviour in self._refs:
            behaviour.stop()
        self._refs = None
        kaa.MainThreadCallback(super(Animation, self).finish, None)()

    def stop(self):
        """
        Stop the animation.
        """
        timeline.stop()
        self.finish()

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return XMLDict(secs=float(element.secs))

    # def __del__(self):
    #     print '__del__', self


class List(object):
    """
    Animation template for new defined animations from the define-animation XML
    node. It contains other animation nodes and optional a properties node.
    """
    candyxml_name = 'define-animation'

    def __init__(self, animations, properties):
        self._animations = animations
        self._properties = properties

    def __call__(self, widget):
        """
        Create the animation bound to the given widget.
        """
        # FIXME: better return InProgressList object
        if self._properties:
            self._properties.apply(widget)
        return [ a(widget) for a in self._animations ]

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the XML element for parameter and create an AnimationTemplate.
        """
        properties = None
        animations = []
        for element in element:
            if element.node == 'properties':
                properties = kaa.candy.Properties.candyxml_create(element)
            elif element.node == 'animation':
                a = element.xmlcreate()
                if a is None:
                    log.error('unknown animation %s', element.style)
                else:
                    animations.append(a)
            else:
                log.error('unknown element %s in define-animation', element.node)
        return cls(animations, properties)

class ExclusiveBehaviour(object):

    effects = []

    def add_widget(self, widget):
        running = widget.get_userdata('running_animations')
        if running is None:
            running = {}
            widget.set_userdata('running_animations', running)
        for effect in self.effects:
            if effect in running:
                running[effect].remove(widget)
            running[effect] = self
        # real add function
        self.apply(widget)

    def remove_widget(self, widget):
        running = widget.get_userdata('running_animations')
        for effect, animation in running.items():
            if animation == self:
                del running[effect]
        # real remove function
        self.remove(widget)

    def stop(self):
        for widget in self.get_actors()[:]:
            self.remove_widget(widget)


class Scale(Animation):
    """
    Zoom-out the given object.
    """
    candyxml_style = 'scale'

    class Behaviour(ExclusiveBehaviour, clutter.BehaviourScale):
        effects = [ 'scale' ]

    def __init__(self, obj, secs, x_factor, y_factor):
        super(Scale, self).__init__(secs)
        s = obj.get_scale()
        scale = Scale.Behaviour(s[0], s[1], x_factor, y_factor, self.alpha)
        scale.apply(obj)
        # give references to start function
        self.start(scale)

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return super(Scale, cls).candyxml_parse(element).update(
            x_factor=float(element.x_factor), y_factor=float(element.y_factor))


class Opacity(Animation):
    """
    Fade in or out the given object.
    """
    candyxml_style = 'opacity'

    class Behaviour(ExclusiveBehaviour, clutter.BehaviourOpacity):
        effects = [ 'opacity' ]

    def __init__(self, obj, secs, stop):
        super(Opacity, self).__init__(secs)
        opacity = Opacity.Behaviour(obj.get_opacity(), stop, self.alpha)
        opacity.add_widget(obj)
        # give references to start function
        self.start(opacity)

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return super(Opacity, cls).candyxml_parse(element).update(
            stop=int(element.stop))


class Move(Animation):
    """
    Move the given object.
    """
    candyxml_style = 'move'

    class Behaviour(ExclusiveBehaviour, clutter.BehaviourPath):
        effects = [ 'move' ]

    def __init__(self, obj, secs, x=None, y=None):
        super(Move, self).__init__(secs)
        x0, y0 = obj.get_position()
        if x is None:
            x = x0
        if y is None:
            y = y0
        path = Move.Behaviour(self.alpha, ((x0, y0), (x, y)))
        path.add_widget(obj)
        # give references to start function
        self.start(path)

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return super(Move, cls).candyxml_parse(element).update(
            x=int(element.x), y=int(element.y))


class ColorChange(Animation):
    """
    Color change animation.
    """
    candyxml_style = 'color'

    class Behaviour(ExclusiveBehaviour, BehaviourColor):
        effects = [ 'color' ]

    def __init__(self, obj, secs, color):
        super(ColorChange, self).__init__(secs)
        a = ColorChange.Behaviour(self.alpha, obj.get_color(), color)
        a.add_widget(obj)
        # give references to start function
        self.start(a)

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the XML element for parameter to create the animation.
        """
        return super(Move, cls).candyxml_parse(element).update(
            x=int(element.x), y=int(element.y))



# register the animations
kaa.candy.xmlparser.register(List)
kaa.candy.xmlparser.register(Scale)
kaa.candy.xmlparser.register(Opacity)
kaa.candy.xmlparser.register(Move)
kaa.candy.xmlparser.register(ColorChange)
