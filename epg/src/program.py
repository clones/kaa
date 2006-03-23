from kaa.strutils import str_to_unicode
from channel import *

class Program(object):
    def __init__(self, channel, start, stop, title, description=u'',
                 subtitle=u'', episode=u'', genre=u'', rating=u""):
        assert(type(channel) == Channel)
        self.channel = channel
        self.start = start
        self.stop = stop
        self.title = title
        self.description = description
        self.subtitle = subtitle
        self.episode = episode
        self.genre = genre
