__all__ = [ 'Canvas' ]

import os
import _weakref
import kaa
from kaa.base import weakref
from kaa.notifier import Signal
from container import *

class Canvas(Container):

    def __init__(self):
        self._queued_children = {}
        self._names = {}

        super(Canvas, self).__init__()

        self.signals = {
            "key_press_event": Signal(),
            "updated": Signal()
        }

        kaa.signals["idle"].connect_weak(self._check_render_queued)
        self._supported_sync_properties += ["fontpath"]

        font_path = []
        for path in ("/usr/share/fonts",):
            for f in os.listdir(path):
                if os.path.isdir(os.path.join(path, f)):
                    font_path.append(os.path.join(path, f))

        self["fontpath"] = font_path


    def _sync_property_fontpath(self):
        self.get_evas().fontpath = self["fontpath"]


    def _sync_property_size(self):
        self._o.viewport_set((0, 0), self["size"])
        self._queue_render()


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
        self._queued_children[_weakref.ref(child)] = 1


    def _check_render_queued(self):
        if len(self._queued_children) == 0 or not self._o:
            return

        needs_render = _weakref.ref(self) in self._queued_children
        queued_children = self._queued_children
        self._queued_children = {}
        for child in queued_children.keys():
            child = child()
            if not child:
                continue
            if child._sync_properties():
                needs_render = True

        if needs_render:
            self._render()


    def _render(self):
        regions = self._o.render()
        #print "@@@ render evas right now", self, regions
        if regions:
            self.signals["updated"].emit(regions)
        return regions

    def _can_sync_property(self, prop):
        return self._o != None


    def _get_actual_size(self):
        return self["size"]
    #
    # Public API
    #

    def render(self):
        self._check_render_queued()


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

    def from_xml(self, filename = None, string = None, path = []):
        xml.create_canvas_tree(self, filename, string, path)

import xml
