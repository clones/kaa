__all__ = [ 'BufferCanvas' ]


from kaa.canvas import Canvas
from kaa import evas


class BufferCanvas(Canvas):
    def __init__(self, size = None, buffer = None):
        super(BufferCanvas, self).__init__()
        if size != None:
            self["size"] = size
            self.create(size, buffer)

    def create(self, size, buffer = None):
        canvas = evas.EvasBuffer(size, depth = evas.ENGINE_BUFFER_DEPTH_BGRA32, buffer = buffer)
        if self["size"] == ("100%", "100%"):
            self["size"] = size
        self._wrap(canvas)
        self._canvased(self)

    def get_buffer(self):
        if not self._o:
            return None
        return self._o.buffer_get()
