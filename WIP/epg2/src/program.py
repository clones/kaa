from kaa.strutils import str_to_unicode
from channel import *

class Program(object):
    def __init__(self, channel, start, stop, title, description):
        assert(type(channel) == Channel)
        self.channel = channel
        self.start = start
        self.stop = stop
        self.title = title
        self.subtitle = u''
        self.episode = u''
        self.description = description
