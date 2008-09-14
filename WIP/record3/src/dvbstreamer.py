import sys
import kaa

class Controller(object):
    def __init__(self):
        self._data = ''
        self._callback = None
        self._requests = []
        self.dvbstreamer = kaa.Process('dvbstreamer')
        self.dvbstreamer.signals['raw-stdout'].connect(self._read)
        self.dvbstreamer.start()
        self.ready = False
        
    def _read(self, data):
        self._data += data
        if self._data.find('DVBStreamer>') >= 0:
            result = self._data[:self._data.find('DVBStreamer>')]
            if self._callback:
                self._callback.finish(result)
                self._callback = None
            if self._requests:
                cmd, self._callback = self._requests.pop(0)
                self.dvbstreamer.write(cmd)
            else:
                self.ready = True
            self._data = self._data[self._data.find('DVBStreamer>')+12:]

    @kaa.coroutine()
    def rpc(self, cmd):
        async = kaa.InProgress()
        if self.ready:
            self.ready = False
            self._callback = async
            self.dvbstreamer.write(cmd + '\n')
        else:
            self._requests.append((cmd + '\n', async))
        yield (yield async)

    @kaa.coroutine()
    def lsservices(self):
        mplex = {}
        for service in (yield self.rpc('lsservices -ls')).split('\n'):
            service = service.strip()
            if not service:
                continue
            info = yield self.rpc('serviceinfo %s' % service)
            service = {}
            for line in info.split('\n'):
                if not line.find(':') > 0:
                    continue
                attr, value = line.split(':', 1)
                service[attr.strip()] = value.strip()
            if not service.get('Multiplex UID'):
                continue
            if not service['Multiplex UID'] in mplex:
                mplex[service['Multiplex UID']] = {}
            mplex[service['Multiplex UID']][service['Name']] = service
        yield mplex

@kaa.coroutine()
def main():
    c = Controller()
    print (yield c.lsservices())
    sys.exit(0)

main()
kaa.main.run()
