import sys
import kaa

class Controller(object):
    def __init__(self, adapter = 0, verbose_level = 0):
        self._data = ''
        self._callback = None
        self._requests = []
        args = ' -v' * verbose_level + ' -a %d' % adapter
        self.dvbstreamer = kaa.Process('dvbstreamer %s' % args)
        self.dvbstreamer.signals['raw-stdout'].connect(self._read)
        self.dvbstreamer.start()
        self.ready = False
        self.mplex = {}
        self.schedulings = []
        # TODO: add timer to call self.lsservices() to gain list of multiplexes/services
        
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
        """
        returns a multiplex dict that contains following information about each service

	DVBStreamer>lsservices -id
	2114.0d01.0002 : arte
	2114.0d01.0003 : Phoenix
	2114.0d01.00a1 : rb TV
	2114.0d01.00a0 : Das Erste
	DVBStreamer>serviceinfo 2114.0d01.00a0
	Name                : Das Erste
	Provider            : ARD
	Type                : Digital TV
	Conditional Access? : Free to Air
	ID                  : 2114.0d01.00a0
	Multiplex UID       : 1220133478
	Source              : 0x00a0
	Default Authority   : (null)
	PMT PID             : 0x0104
	    Version         : 2
	"""
        mplex = {}
        for service in (yield self.rpc('lsservices -id')).splitlines():
            service = service.strip()
            if not service:
                continue
            service_id, service_name = service.split(' : ',1)

            info = yield self.rpc('serviceinfo %s' % service_id)
            service = {}
            for line in info.split('\n'):
                if not line.find(':') > 0:
                    continue
                attr, value = line.split(':', 1)
                service[attr.strip()] = value.strip()

            if not service.get('Multiplex UID'):
                # service id contains multiplex uid
                service['Multiplex UID'] = '.'.join(service_id.split('.')[0:1])

            if not service['Multiplex UID'] in mplex:
                mplex[service['Multiplex UID']] = {}
            mplex[service['Multiplex UID']][service['Name']] = service
        self.mplex = mplex
        yield mplex

    @kaa.coroutine()
    def _start_recording(self):
        # add new service filter ==> remember which service that is
        pass

    @kaa.coroutine()
    def _stop_recording(self):
        # remove corresponding service filter
        pass

    @kaa.coroutine()
    def scheduler(self):
        # 1) iterate over all schedulings and check if there's a scheduling that
        #    a) is currently not in RUNNING state AND
        #    b) is currently not in FINISHED state AND
        #    c) starts within the next 5 seconds or should have started already AND
        #    d) has not reached it's enddate
        #    ==>
        #    1) start recording to target_url
        #    2) update state of scheduling to RUNNING
        #    3) emit event that scheduling_id has now state RUNNING
        #
        # 2) iterate over all schedulings and check if there's a scheduling that
        #    a) is currently in RUNNING state AND
        #    b) has not reached it's enddate
        #    ==>
        #    1) stop recording
        #    2) emit event that scheduling_id has now state FINISHED
        pass

    @kaa.coroutine()
    def add_scheduling(self, service_id, target_url, time_start, time_end):
        # 1) check if service_id is valid and known
        # 2) check if target_url is valid
        # 3) check if time_start and time_end are valid
        #    1) check if the date values are valid
        #    2) check if date values are both in the past
        # 4) check if there's a colliding scheduling
        #    ( (time_start1 <= time_start2 <= time_end1) ||
        #      (time_start1 <= time_end2   <= time_end1) ||
        #      (time_start2 <= time_start1 <= time_end2) ||
        #      (time_start2 <= time_end1   <= time_end2) )
        #    ==> yes, is it
        #    1) check if colliding scheduling uses same multiplex
        #       ==> yes, it does ==> no problem
        #       ==> no, it doesn't ==> ERROR
        # 5) update timer for calling self.scheduler() at the right time
        #    1) if new scheduling starts now then call scheduler NOW
        #    2) calculate start of next recording and set timer for calling scheduler later on
        pass

    @kaa.coroutine()
    def update_scheduling(self, scheduling_id, target_url, time_start, time_end):
        pass

    @kaa.coroutine()
    def remove_scheduling(self, scheduling_id, force = False):
        pass

    @kaa.coroutine()
    def list_schedulings(self):
        pass

    

@kaa.coroutine()
def main():
    c = Controller()
    print (yield c.lsservices())
    sys.exit(0)

main()
kaa.main.run()
