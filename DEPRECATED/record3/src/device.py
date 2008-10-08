class Device(object):

    def __init__(self):
        self.channels = {}

    def get_channel(self, name):
        return self.channels.get(name)

    def add_channel(self, name, tuning_data, access_data):
        self.channels[name] = tuning_data, access_data

    def get_channels(self):
        result = {}
        for name, (tuning_data, access_data) in self.channels.items():
            if not str(tuning_data) in result:
                result[str(tuning_data)] = []
            result[str(tuning_data)].append(name)
        return result.values()

    def read_channels_conf(self, filename):
        for line in open(filename).readlines():
            self.add_channel(*self._read_channels_conf_line(line.strip()))

    def add(self, channel, sink):
        raise NotImplementedError

    def remove(self, channel, sink):
        raise NotImplementedError

    def _read_channels_conf_line(self, line):
        raise NotImplementedError

