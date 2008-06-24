# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# progressbar.py - Progressbar Widget
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

# gui imports
import kaa.candy
import core

class Progressbar(core.Group):
    """
    Widget showing a progressbar. Only the bar is drawn, the border has
    to be created ouside this widget.
    """
    __gui_name__ = 'progressbar'

    def __init__(self, pos, size, progress):
        super(Progressbar, self).__init__(pos, size)
        self._width = size[0]
        self._max = 0
        self._progress = progress(pos=(0,0), size=size)
        self._progress.set_width(1)
        self._progress.show()
        self.add(self._progress)

    @kaa.candy.gui_execution()
    def set_max(self, max):
        """
        Set maximum value of the progress.
        """
        self._max = max

    @kaa.candy.gui_execution()
    def set_progress(self, value):
        """
        Set a new progress and redraw the widget.
        """
        pos = float(value) / max(self._max, value, 0.1)
        self._progress.set_width(int(max(pos * self._width, 1)))

    @classmethod
    def parse_XML(cls, element):
        """
        Parse the XML element for parameter to create the widget.
        """
        return super(Progressbar, cls).parse_XML(element).update(
            progress=element[0].xmlcreate())

# register widget to the core
kaa.candy.xmlparser.register(Progressbar)
