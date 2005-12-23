__all__ = ['Animation']

from image import *
from kaa import notifier
import os

try:
    from kaa.canvas import _mng
except ImportError:
    _mng = None

MNG_MAGIC = "\x8aMNG\x0d\x0a\x1a\x0a"

class Animation(Image):
    def __init__(self, file = None):
        super(Animation, self).__init__(file)

        self._mng = None
        self._update_frame_timer = notifier.WeakTimer(self._update_frame)

        if file:
            self.set_image(file)


    def _mng_refresh(self, x, y, w, h):
        self.set_dirty((x, y, w, h))


    def _mng_update(self):
        delay = self._mng.update()
        while delay == 1:
            delay = self._mng.update()

        if delay == 0:
            self._update_frame_timer.stop()
            return

        delay /= 1000.0
        cur_interval = self._update_frame_timer.get_interval()
        if cur_interval and abs(delay - cur_interval) > 0.02 or \
           not self._update_frame_timer.active():
            self._update_frame_timer.start(delay)


    def _update_frame(self):
        if self._mng:
            self._mng_update()


    def _sync_property_data(self):
        self._update_frame()
        super(Animation, self)._sync_property_data()


    def set_image(self, file):
        if isinstance(file, basestring):
            try:
                f = open(file)
            except:
                raise ValueError, "Unable to open file: %s" % file
            
            bytes = f.read()
            if bytes[:len(MNG_MAGIC)] != MNG_MAGIC:
                raise ValueError, "File '%s' is not a MNG file" % file

            if not _mng:
                raise ValueError, "MNG support has not been enabled"

            self._mng = _mng.MNG(notifier.WeakCallback(self._mng_refresh))
            width, height, delay, buffer = self._mng.open(bytes)

            self.set_data(width, height, buffer, copy = False)
        else:
            raise ValueError, "Only filenames supported right now"


    def stop(self):
        self._update_frame_timer.stop()

    def start(self):
        self._update_frame()

    def is_playing(self):
        return self._update_frame_timer.active()

