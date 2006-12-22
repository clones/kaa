class Filter(object):

    def __init__(self, name):
        self.name = name
        self.prop = {}
        self._obj = None

    def set_parameters(self, **kwargs):
        self.prop.update(kwargs)
        if self._obj:
            self._obj.set_parameters(**kwargs)

    def create(self, xine, video_targets=[], audio_targets=[]):
        self._obj = xine.post_init(self.name, video_targets = video_targets,
                                   audio_targets = audio_targets)
        self._obj.set_parameters(**self.prop)
        return self._obj


    def get_default_input(self):
        return self._obj.get_default_input()

    
class FilterChain(object):

    def __init__(self):
        self._filter = {}


    def get(self, name):
        f = self._filter.get(name)
        if not f:
            f = Filter(name)
            self._filter[name] = f
        return f


    def wire(self, xine, src, chain, dst):
        chain = chain[:]
        chain.reverse()
        for f in chain:
            f = self.get(f)
            f.create(xine, video_targets = [ dst ])
            dst = f.get_default_input()

        # FIXME: rewrire support
        src.wire(dst)
