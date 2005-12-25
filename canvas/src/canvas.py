__all__ = [ 'Canvas' ]

import os
import _weakref
import kaa
from kaa.base import weakref
from kaa.notifier import Signal, WeakCallback
from container import *
try:
    from kaa import imlib2
except ImportError:
    imlib2 = None

class Canvas(Container):

    def __init__(self):
        self._queued_children = {}
        #self._queued_children = []
        self._names = {}

        super(Canvas, self).__init__()

        self.signals = {
            "key_press_event": Signal(),
            "updated": Signal()
        }

        kaa.signals["idle"].connect(WeakCallback(self._render_queued))
        self._supported_sync_properties += ["fontpath"]

        font_path = []
        for path in ("/usr/share/fonts",):
            for f in os.listdir(path):
                if os.path.isdir(os.path.join(path, f)):
                    font_path.append(os.path.join(path, f))

        self["fontpath"] = font_path

    def __str__(self):
        clsname = self.__class__.__name__
        return "<canvas.%s size=%s>" % (clsname, self["size"])


    def _update_debug_rectangle(self):
        # Don't draw debug rectangle for canvases
        return

    def _sync_property_fontpath(self):
        self.get_evas().fontpath = self["fontpath"]
        if imlib2:
            for path in self["fontpath"]:
                imlib2.add_font_path(path)


    def _sync_property_size(self):
        super(Canvas, self)._sync_property_size()
        if self["size"] != self._o.viewport_get()[1]:
            self._o.viewport_set((0, 0), self["size"])
            self._queue_render()
        return True

    def _register_object_name(self, name, object):
        # FIXME: handle cleanup
        self._names[name] = weakref(object)

    def _unregister_object_name(self, name):
        if name in self._names:
            del self._names[name]

    def _get_property_pos(self):
        return 0, 0

    def _queue_render(self, child = None):
        if not child:
            child = self
        super(Canvas, self)._queue_render(child)


    def _render_queued(self):
        if not self._o:
            return
        import time
        t0=time.time()
        if super(Canvas, self)._render_queued():
            t1=time.time()
            regions = self._render()
            #print "@@@ render evas right now", time.time()-t0, self, regions, " - inside evas", time.time()-t1



    def _render(self):
        regions = self._o.render()
        if regions:
            self.signals["updated"].emit(regions)
        return regions

    def _can_sync_property(self, prop):
        return self._o != None


    def _get_actual_size(self):
        return self["size"]

    def _request_reflow(self, what_changed = None, old = None, new = None, child_asking = None):
        if what_changed == "layer":
            return super(Canvas, self)._request_reflow(what_changed, old, new, child_asking)
        # Size of direct children of the root object (canvas) can't affect each other.
        return

    
    #
    # Public API
    #

    def render(self):
        self._render_queued()


    def get_evas(self):
        return self._o

    def get_canvas(self):
        return self

    def find_object(self, name):
        if name in self._names:
            object = self._names[name]
            if object:
                return object._ref()
            # Dead weakref, remove it.
            del self._names[name]

    def clip(self, pos = (0,0), size = (-1,-1)):
        raise CanvasError, "Can't clip whole canvases yet -- looks like a bug in evas."

    def add_font_path(self, path):
        self["fontpath"] = self["fontpath"] + [path]

    def remove_font_path(self, path):
        if path in self["fontpath"]:
            fp = self["fontpath"]
            fp.remove(path)
            self["fontpath"] = fp

    def from_xml(self, filename_or_string, classname = None, path = []):
        xml.create_canvas_tree(filename_or_string, self, classname, path)

import xml
