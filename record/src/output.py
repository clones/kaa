import _op

class Filewriter(object):
    FT_RAW  = 0
    FT_MPEG = 1

    def __init__(self, filename, chunksize, type):
        self.filename = filename
        self.chunksize = chunksize
        if not type in (self.FT_RAW, self.FT_MPEG):
            raise AttributeError('Invalid type')
        self.type = type
        
    def _create_plugin(self):
        return _op.Filewriter(self.filename, self.chunksize, self.type)
