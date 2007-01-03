class FilterChain(object):

    def __init__(self, xine, video_targets=[], audio_targets=[]):
        self._filter = {}
        self._chain = []
        self._xine = xine
        self._video_targets = video_targets
        self._audio_targets = audio_targets


    def get(self, name):
        f = self._filter.get(name)
        if not f:
            f = self._xine.post_init(name, video_targets = self._video_targets,
                                     audio_targets = self._audio_targets)
            self._filter[name] = f
        return f


    def get_chain(self):
        return self._chain[1:]


    def rewire(self, *chain):
        self.wire(self._chain[0], *chain)

        
    def wire(self, src, *chain):
        self._chain = [ src ] + list(chain)
        for f in chain:
            f = self.get(f)
            src.wire(f.get_default_input())
            src = f.get_default_output()

        # FIXME: what target?
        src.wire(self._video_targets[0])
