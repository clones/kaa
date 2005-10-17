from kaa.base.utils import str_to_unicode
from channel import *

class Program(object):
    def __init__(self, channel, start, stop, title, desc):
        assert(type(channel) == Channel)
        self.channel = channel
        self.start = start
        self.stop = stop
        self.title = title
        self.desc = desc
