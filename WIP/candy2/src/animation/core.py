# python imports
import _weakref
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

    def __init__(self, secs):
        super(Animation, self).__init__()
        timeline = clutter.Timeline(int(float(secs) * FPS), FPS)
        timeline.set_loop(False)
        # FIXME: do not hardcode alpha function
        self.alpha = clutter.Alpha(timeline, clutter.ramp_inc_func)

    def start(self, widgets, behaviour):
        """
        Start the animation.
        """
        # store reference to the behaviour or the animation won't run
        for widget in widgets:
            current = widget.get_userdata('__animations__') or {}
            for e in behaviour.effects:
                # set behaviour for the efect. This may override
                # existing behaviour with the same effect, they
                # will be removed to avoid race conditions.
                current[e] = behaviour
            # This creates a circular reference which will be resolved
            # on the destroy signal callback in widgets/core.py
            # FIXME: this is all far away from perfect
            widget.set_userdata('__animations__', current)
        timeline = self.alpha.get_timeline()
        timeline.rewind()
        timeline.start()
        self.alpha = None
        # it this pount we have no references anymore. Neither to
        # the running timeline not to the alpha. The only existing
        # reference to the behaviour is in the widgets and that will
        # be destroyed once the widget is destroyed
        # Store a weakref to the behaviour to emit finished when the
        # behaviour is gone because it will not be triggered ever
        # if we do not do this.
        timeline.connect('completed', self._clutter_finish)
        self._weak_behaviour = _weakref.ref(behaviour, self._clutter_finish)

    def _clutter_finish(self, result):
        """
        Callback from any thread when the animation is finished.
        """
        self._weak_behaviour = None
        kaa.MainThreadCallback(self.finish)(None)

    def finish(self, result):
        """
        Callback in the mainthread when the animation is finished.
        """
        if not self._finished:
            super(Animation, self).finish(result)
            
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


class Scale(Animation):
    """
    Zoom-out the given object.
    """
    candyxml_style = 'scale'

    class Behaviour(clutter.BehaviourScale):
        effects = [ 'scale' ]

    def __init__(self, obj, secs, x_factor, y_factor):
        super(Scale, self).__init__(secs)
        s = obj.get_scale()
        scale = Scale.Behaviour(s[0], s[1], x_factor, y_factor, self.alpha)
        scale.apply(obj)
        # give references to start function
        self.start([obj], scale)

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

    class Behaviour(clutter.BehaviourOpacity):
        effects = [ 'opacity' ]

    def __init__(self, obj, secs, stop):
        try:
            super(Opacity, self).__init__(secs)
        except Exception, e:
            print e
        opacity = Opacity.Behaviour(obj.get_opacity(), stop, self.alpha)
        opacity.apply(obj)
        # give references to start function
        self.start([obj], opacity)

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

    class Behaviour(clutter.BehaviourPath):
        effects = [ 'move' ]

    def __init__(self, obj, secs, x=None, y=None):
        super(Move, self).__init__(secs)
        x0, y0 = obj.get_position()
        if x is None:
            x = x0
        if y is None:
            y = y0
        path = Move.Behaviour(self.alpha, ((x0, y0), (x, y)))
        path.apply(obj)
        # give references to start function
        self.start([obj], path)

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

    class Behaviour(BehaviourColor):
        effects = [ 'color' ]

    def __init__(self, obj, secs, color):
        super(ColorChange, self).__init__(secs)
        a = ColorChange.Behaviour(self.alpha, obj.get_color(), color)
        a.apply(obj)
        # give references to start function
        self.start([obj], a)

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
