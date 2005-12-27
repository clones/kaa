__all__ = [ 'X11Canvas' ]

from kaa.canvas import Canvas
from kaa import display
from kaa import evas


class X11Canvas(Canvas):

    def __init__(self, size, use_gl = None, title = "Canvas"):
        if use_gl == None:
            use_gl = "gl_x11" in evas.render_method_list()

        self._window = display.X11Window(size = size, title = "Kaa Display Test")
        self._canvas_window = display.EvasX11Window(use_gl, size = size, parent = self._window)
        self._canvas_window.show()
        super(X11Canvas, self).__init__()

        self["size"] = size
        
        self._wrap(self._canvas_window.get_evas())

        self._canvas_window.signals["key_press_event"].connect_weak(self.signals["key_press_event"].emit)
        self._window.signals["resize_event"].connect_weak(self._handle_resize_event)
        self._canvas_window.set_cursor_hide_timeout(1)


    def _handle_resize_event(self, old_size, size):
        self._canvas_window.resize(size)
        self._o.output_size_set(size)
        #self.resize(size)
        self._queue_render()

    def _set_property_visible(self, vis):
        # Delay window hide/show until next render, because we want the
        # the render to happen before the window gets shown.
        self._visibility_on_next_render = vis
        self._queue_render()
        self._set_property_generic("visible", vis)


    def _render(self):
        vis = self._visibility_on_next_render
        if vis == False:
            self._window.hide()
        regions = self._o.render()
        if vis == True:
            self._window.show()

        self._visibility_on_next_render = None
        if regions:
            self.signals["updated"].emit(regions)
        return regions

    def get_window(self):
        return self._window
