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
        print 'a'
        regions = self._o.render()
#         if vis == True:
#             self._window.show()

#         self._visibility_on_next_render = None
        if regions:
            self.signals["updated"].emit(regions)
        return regions

#     def get_window(self):
#         return self._window
