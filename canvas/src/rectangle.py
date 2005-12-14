__all__ = [ 'Rectangle' ]

from object import *

class Rectangle(Object):

    def __init__(self, size = None, color = None):
        super(Rectangle, self).__init__()

        if size:
            self.resize(size)
        if color:
            self.set_color(*color)
   
    def _canvased(self, canvas):
        super(Rectangle, self)._canvased(canvas)
        if not self._o and canvas.get_evas():
            o = canvas.get_evas().object_rectangle_add()
            self._wrap(o)
