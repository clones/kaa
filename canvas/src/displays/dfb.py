__all__ = [ 'DirectFBCanvas' ]

from kaa.canvas import Canvas
from kaa.display.dfb import EvasDirectFB

class DirectFBCanvas(Canvas):

    def __init__(self, size):
        self._dfb = EvasDirectFB(size)
        super(DirectFBCanvas, self).__init__()

        self["size"] = size

        self._wrap(self._dfb.get_evas())

    def _render(self):
        regions = self._o.render()
        if regions:
            self.signals["updated"].emit(regions)
        return regions
