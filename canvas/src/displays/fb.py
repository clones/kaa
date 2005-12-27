__all__ = [ 'FBCanvas' ]

from kaa.canvas import Canvas
from kaa.display import EvasFramebuffer


class FBCanvas(Canvas):

    def __init__(self, fbset=None):
        self._fb = EvasFramebuffer(fbset)
        super(FBCanvas, self).__init__()

        self["size"] = self._fb.size()

        self._wrap(self._fb.get_evas())

    def _render(self):
        regions = self._o.render()
        if regions:
            self.signals["updated"].emit(regions)
        return regions
