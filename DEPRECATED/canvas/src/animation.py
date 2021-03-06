# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------------
# kaa.canvas - Canvas library based on kaa.evas
# Copyright (C) 2005, 2006 Jason Tackaberry
#
# First Edition: Jason Tackaberry <tack@sault.org>
# Maintainer:    Jason Tackaberry <tack@sault.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

import kaa
import time, math, _weakref

__all__ = ["animate", "register_animator_method"]

_methods = {}
_queue = {}

def _step_animators():
    if len(_queue) == 0:
        _step_animators_timer.stop()

    for animators in _queue.values():
        for anim in animators:
            anim.step()

_step_animators_timer = kaa.Timer(_step_animators)
_step_animators_timer.restart_when_active = False


def animate(o, method, **kwargs):
    if method not in _methods:
        raise ValueError, "Unknown animator method '%s'" % method
    
    anim = _methods[method](o, **kwargs)
    # The timer value defines the framerate of the animation.  This value
    # could be determined based on CPU speed.
    _step_animators_timer.start(0.01)
    return anim



def register_animator_method(method, cls):
    _methods[method] = cls


def _calc_step_value_linear(begin_val, end_val, time_offset, duration):
    return int((end_val - begin_val) * (time_offset / duration))

def _calc_step_value_log(begin_val, end_val, time_offset, duration):
    p = max(1.0, (time_offset / duration) * 10.0)
    factor = math.log(p, 10.0)
    return int((end_val - begin_val) * factor)

def _calc_step_value_exp(begin_val, end_val, time_offset, duration):
    p = (time_offset / duration) * 10.0
    factor = (math.pow(1.3, p)-1) / (1.3**10)
    return int((end_val - begin_val) * factor)



class Animator(object):
    def __init__(self, o, **kwargs):
        self._running = False
        self._object = _weakref.ref(o)
        self._end_callback = kwargs.get("end_callback")
        self._duration = kwargs.get("duration")
        self._accelerate = kwargs.get("accelerate")
        self._decelerate = kwargs.get("decelerate")
        self._bounce = kwargs.get("bounce")
        self._bounce_factor = kwargs.get("bounce_factor", 0.1)
        self._did_bounce = False
        self._target = None

        if self._duration == None:
            # Default to one second if duration isn't specified.
            self._duration = 1.0

        self._set_end_point(**kwargs)

        if not kwargs.get("deferred"):
            self.start()


    def _apply_state(self, state):
        # Must be subclassed.
        pass


    def _compute_target(self, target):
        # Must be subclassed.
        return target


    def _get_state(self):
        # Must be subclassed.
        return None


    def _clamp(self, value, max_value, dir, index):
        if (dir < 0 and value <= max_value) or \
           (dir > 0 and value >= max_value):
           return max_value

        return value


    def _apply_step(self, start_state, target, computed_target, time_offset, duration):
        value = [None] * len(computed_target)
        for i in range(len(value)):
            if computed_target[i] == None:
                continue

            val_offset = self._calc_step_value(start_state[i], computed_target[i], time_offset, duration)
            new_value = (start_state[i] + int(val_offset))
            value[i] = self._clamp(new_value, computed_target[i], self._direction[i], i)

        if value == computed_target:
            if self._bounce and not self._did_bounce:
                self._apply_state(value)
                self._start_time = None
                self._did_bounce = True
            else:
                self._apply_state(target)
                return True
        else:
            self._apply_state(value)


    def _set_end_point(self, **kwargs):
        self._start_time = None
        self._did_bounce = False


    def _begin_first_step(self, target, computed_target, start_state):
        self._direction = [1] * len(computed_target)
        for i in range(len(self._direction)):
            if computed_target[i] == None:
                continue
            if computed_target[i] < start_state[i]:
                self._direction[i] = -1
            if self._bounce and not self._did_bounce:
                distance = computed_target[i] - start_state[i]
                computed_target[i] += int(distance * self._bounce_factor)


    def _calc_step_value(self, begin_val, end_val, time_offset, duration):
        if duration == 0:
            return end_val - begin_val

        if self._did_bounce:
            duration /= 2.0
        if self._accelerate and not self._did_bounce:
            func = _calc_step_value_exp
        elif self._decelerate and not self._did_bounce:
            func = _calc_step_value_log
        else:
            func = _calc_step_value_linear

        retval = func(begin_val, end_val, time_offset, duration)
        return retval

    def _animation_ended(self):
        self.stop()

    def _can_animate(self):
        return True


    def _step(self):
        if self._start_time == None:
            # First step
            self._start_time = time.time()
            self._start_state = self._get_state()
            self._computed_target = self._compute_target(self._target)
            self._begin_first_step(self._target, self._computed_target, self._start_state)

        time_offset = time.time() - self._start_time
        if self._apply_step(self._start_state, self._target, self._computed_target, 
                            time_offset, self._duration) == True:
            self._animation_ended()
            if self._end_callback:
                self._end_callback()


    def step(self):
        if not self._object():
            # Weakref is dead.
            self.stop()
            return

        if not self._can_animate():
            return

        self._step()


    def start(self):
        if self._running:
            return

        self._running = True
        self._did_bounce = False

        if self._object in _queue:
            # Delete other animator of this type for this object.
            for animator in _queue[self._object]:
                if isinstance(animator, type(self)):
                    _queue[self._object].remove(animator)

            _queue[self._object].append(self)
        else:
            _queue[self._object] = [self]


    def stop(self):
        self._running = False

        if self._object not in _queue:
            return
        if self not in _queue[self._object]:
            return

        _queue[self._object].remove(self)

        if len(_queue[self._object]) == 0:
            del _queue[self._object]




class SizeAnimator(Animator):

    def _set_end_point(self, **kwargs):
        super(SizeAnimator, self)._set_end_point(**kwargs)
        self._target = kwargs.get("width"), kwargs.get("height")

    def _can_animate(self):
        return "size" not in self._object()._changed_since_sync

    def _get_state(self):
        return self._object()._get_intrinsic_size()

    def _apply_state(self, state):
        self._object().resize(*state)

    def _compute_target(self, target):
        computed_target = list(self._object()._compute_size(target, None))
        for i in range(2):
            if target[i] == -1:
                computed_target[i] = None
        return computed_target


    def _clamp(self, value, max_value, dir, index):
        if (index == 1 and self._object().get_hcenter() != None) or \
           (index == 0 and self._object().get_vcenter() != None):
            # Clamp value to multiple of two if this dimension is centered.
            value &= ~1

        ret_value = super(SizeAnimator, self)._clamp(value, max_value, dir, index)
        return ret_value


class ScaleAnimator(SizeAnimator):

    def _apply_state(self, state):
        print "SIZE", state
        self._object().scale(*state)


class PositionAnimator(Animator):
    def __init__(self, o, **kwargs):
        super(PositionAnimator, self).__init__(o, **kwargs)
        
        # We want to know if the object is resized since our target position
        # may depend on it.  With a weak ref, when the animator is done and
        # deleted, the callback will be automatically disconnected.
        o.signals["resized"].connect_weak(self._object_resized)


    def _object_resized(self, old_pos, new_pos):
        # Object has been resized, so recompute new target position in case
        # the target depends on the size.
        self._computed_target = self._compute_target(self._target)
        if self._can_animate() or self._start_time != None:
            self._step()


    def _can_animate(self):
        return "pos" not in self._object()._changed_since_sync


    def _set_end_point(self, **kwargs):
        super(PositionAnimator, self)._set_end_point(**kwargs)
        self._target = kwargs.get("left"), kwargs.get("top"), \
                       kwargs.get("right"), kwargs.get("bottom"), \
                       kwargs.get("hcenter"), kwargs.get("vcenter")


    def _get_state(self):
        return self._object()._get_computed_pos()

    def _apply_state(self, state):
        self._object().move(*state)

    def _compute_target(self, target):
        return list(self._object()._compute_pos(target, None)[0])
        



class ColorAnimator(Animator):

    def _set_end_point(self, **kwargs):
        super(ColorAnimator, self)._set_end_point(**kwargs)
        self._target = kwargs.get("r"), kwargs.get("g"), kwargs.get("b"), kwargs.get("a")

    def _can_animate(self):
        return "color" not in self._object()._changed_since_sync

    def _get_state(self):
        return self._object().get_color()

    def _apply_state(self, state):
        self._object().set_color(*state)

    def _compute_target(self, target):
        return list(target)



class OpacityAnimator(ColorAnimator):
    def __init__(self, o, **kwargs):
        kwargs["a"] = int(kwargs["opacity"] * 255)
        super(OpacityAnimator, self).__init__(o, **kwargs)



class SequenceAnimator(Animator):
    def __new__(cls, o, **kwargs):
        submethod = kwargs.get("submethod")
        if submethod not in _methods:
            raise ValueError, "Unknown animator method '%s'" % submethod

        cls = type("SequenceAnimator", (cls, _methods[submethod]), {})
        return super(SequenceAnimator, cls).__new__(cls, o, **kwargs)

    def __init__(self, o, **kwargs):
        if "sequence" not in kwargs:
            kwargs["deferred"] = True
        self._loop = kwargs.get("loop")

        super(SequenceAnimator, self).__init__(o, **kwargs)

        if "sequence" in kwargs:
            self.set_sequence(kwargs["sequence"])

    def set_sequence(self, sequence):
        assert(isinstance(sequence, (list, tuple)))
        self._sequence = sequence
        self._cur_stage = 0
        self._set_end_point(**self._sequence[0])
        self.start()


    def _animation_ended(self):
        self._cur_stage += 1
        if self._cur_stage >= len(self._sequence):
            if self._loop:
                self._cur_stage = 0
            else:
                return super(SequenceAnimator, self)._animation_ended()

        self._set_end_point(**self._sequence[self._cur_stage])



class ThrobAnimator(SequenceAnimator):
    def __new__(cls, o, **kwargs):
        return super(ThrobAnimator, cls).__new__(cls, o, submethod = "size")

    def __init__(self, o, **kwargs):
        super(ThrobAnimator, self).__init__(o, loop = True, **kwargs)
        step1 = {"width": kwargs.get("width"), "height": kwargs.get("height")}
        step2 = {}
        if "width" in kwargs:
            step2["width"] = o["size"][0]
        if "height " in kwargs:
            step2["height"] = o["size"][1]

        self.set_sequence([step1, step2])



register_animator_method("size", SizeAnimator)
register_animator_method("scale", ScaleAnimator)
register_animator_method("move", PositionAnimator)
register_animator_method("color", ColorAnimator)
register_animator_method("opacity", OpacityAnimator)
register_animator_method("sequence", SequenceAnimator)
register_animator_method("throb", ThrobAnimator)

