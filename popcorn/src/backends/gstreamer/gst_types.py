import kaa.notifier
from kaa.weakref import weakref


class Status(object):
    IDLE    = 1
    OPENING = 2
    PLAYING = 3

    def __init__(self, monitor):
        self._value = Status.IDLE
        self._timer = kaa.notifier.WeakTimer(monitor)
        self._callback = monitor
        
    def set_status(self, status):
        if self._value == status:
            return
        self._value = status
        self._callback()
        if status == Status.PLAYING:
            self._timer.start(0.1)
        if status == Status.IDLE:
            self._timer.stop()

    def get_status(self):
        return self._value
