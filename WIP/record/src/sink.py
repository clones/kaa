__all__ = [ 'Filewriter' ]

import pygst
pygst.require('0.10')
import gst

class Filewriter(object):
    def __init__(self, filename):
        self.element = gst.element_factory_make('filesink')
        self.element.set_property('location', filename)
