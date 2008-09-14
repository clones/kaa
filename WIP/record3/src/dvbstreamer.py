import sys
import kaa
import time
import logging
import uuid
log = logging.getLogger('dvbstreamer')


class Scheduling(object):
	def __init__(self, mplex, service_id, target_url, time_start, time_end, state = 'SCHEDULED'):
		self.sid = str( uuid.uuid4() ) # scheduling id
		self.state = state	# possible states: ERROR, SCHEDULED, RUNNING, FINISHED
		self.mplex = mplex
		self.service_id = service_id
		self.target_url = target_url
		self.time_start = time_start
		self.time_end = time_end

	def id(self):
		return self.sid

	def state(self):
		return self.state

	def is_state(self, state):
		return (self.state == state)


class Controller(object):
	def __init__(self, adapter = 0, verbose_level = 0):
		log.debug('new controller: adapter=%s, verbose_level=%s' % (adapter, verbose_level))
		self._data = ''
		self._callback = None
		self._requests = []
		cmd = 'dvbstreamer ' + ' -v' * verbose_level + ' -a %d' % adapter
		log.debug('calling dvbstreamer: %s' % cmd)
		self.dvbstreamer = kaa.Process(cmd)
		self.dvbstreamer.signals['raw-stdout'].connect(self._read)
		self.dvbstreamer.signals['completed'].connect(self._dvbstreamer_died)
		self.dvbstreamer.start()
		self.ready = False
		self.mplex = {}
		self.schedulings = {}
		self.selected_service = None
		kaa.OneShotTimer(self.lsservices).start(0.0)
		
	def _dvbstreamer_died(self, data):
		log.error('dvbstreamer died! exitcode=%s' % data)
		
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
	Name				: Das Erste
	Provider			: ARD
	Type				: Digital TV
	Conditional Access? : Free to Air
	ID					: 2114.0d01.00a0
	Multiplex UID		: 1220133478
	Source				: 0x00a0
	Default Authority	: (null)
	PMT PID				: 0x0104
		Version			: 2
	"""
		log.debug('lsservices()')
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
#		 log.debug('lsservices()=%s' % mplex)
		yield mplex


	@kaa.coroutine()
	def _start_recording(self, scheduling_id):
		log.info('starting recording of %s' % scheduling_id)
		if not self.schedulings.has_key( scheduling_id ):
			log.error('scheduling %s does not exist!' % scheduling_id)
			raise Exception('ERROR: cannot start unknown scheduling')

		sched = self.schedulings[ scheduling_id ]
		# switch to new multiplex and service
		if self.selected_service != sched.service_id:
			log.info('selected service="%s"	  selecting new service="%s"' % (self.selected_service, sched.service_id))
			yield self.rpc( 'select %s' % sched.service_id )

		# add service filter
		yield self.rpc( 'addsf %s %s' % (scheduling_id, sched.target_url) )
		yield self.rpc( 'setsf %s %s' % (scheduling_id, sched.service_id) )

		# set state to "RUNNING"
		sched.state = 'RUNNING'


	@kaa.coroutine()
	def _stop_recording(self, scheduling_id):
		log.info('stopping recording of %s' % scheduling_id)
		if not self.schedulings.has_key( scheduling_id ):
			log.error('scheduling %s does not exist!' % scheduling_id)
			raise Exception('ERROR: cannot start unknown scheduling')

		sched = self.schedulings[ scheduling_id ]

		# add service filter
		yield self.rpc( 'setsfmrl %s null://' % scheduling_id )
		yield self.rpc( 'rmsf %s' % scheduling_id)

		# set state to "FINISHED"
		sched.state = 'FINISHED'


	@kaa.coroutine()
	def scheduler(self):
		now = time.time()

		# 1) iterate over all schedulings and check if there's a scheduling that
		#	 a) is currently in RUNNING state AND
		#	 b) has not reached it's enddate
		#	 ==>
		#	 1) stop recording
		#	 2) emit event that scheduling_id has now state FINISHED
		for sched in self.schedulings.values():
			if sched.is_state('RUNNING') and sched.time_end < now:
				yield self._stop_recording(sched.id())
				# TODO FIXME emit signal that recording of scheduling is finished

		# 2) iterate over all schedulings and check if there's a scheduling that
		#	 a) is currently in SCHEDULED state AND
		#	 b) starts within the next 5 seconds or should have started already AND
		#	 c) has not reached it's enddate
		#	 ==>
		#	 1) start recording to target_url
		#	 2) update state of scheduling to RUNNING
		#	 3) emit event that scheduling_id has now state RUNNING
		for sched in self.schedulings.values():
			if sched.is_state('SCHEDULED') and sched.time_start < now and now < sched.time_end:
				yield self._start_recording(sched.id())

		# 3) update timer for calling self.scheduler() at the right time
		#	 calculate start of next recording and set timer for calling scheduler later on

		# call scheduler every 5 minutes or more often
		next_event = now + 300
		for sched in self.schedulings.values():
			if sched.is_state('SCHEDULED') and sched.time_start < next_event:
				next_event = sched.time_start
			if sched.is_state('RUNNING') and sched.time_end < next_event:
				next_event = sched.time_end
		# add delay of 0.05 seconds to make sure, recording has started at next check
		log.info('scheduler: calling scheduler in %2.4f seconds' % (next_event - now + 0.05))
		kaa.OneShotTimer(self.scheduler).start(next_event - now + 0.05)

		yield None

	def _get_mplex(self, service_id):
		""" returns mplex uid for specified service or service_id """
		if not self.mplex:
			return None
		for mplex, servicelist in self.mplex.items():
			for service_name, service in servicelist.items():
				if service.get('ID') == service_id:
					return service.get('Multiplex UID')
				if service.get('Name') == service_id:
					return service.get('Multiplex UID')
		return None

	@kaa.coroutine()
	def add_scheduling(self, service_id, target_url, time_start, time_end):
		log.debug('add_scheduling: service_id="%s"	time_start=%s  time_end=%s	target_url="%s"' % 
				  (service_id, time_start, time_end, target_url))

		# 1) check if service_id is valid and known
		mplex = self._get_mplex( service_id )
		if not mplex:
			log.error( 'add_scheduling: unknown service_id (%s)' % service_id )
			raise Exception( 'INVALID_SERVICE_ID' )

		# 2) check if target_url is valid
		if not (target_url.startswith('file://') or target_url.startswith('udp://')):
			log.error( 'add_scheduling: invalid target_url (%s)' % target_url )
			raise Exception( 'INVALID_TARGET_URL' )

		# 3) check if time_start and time_end are valid
		#	 1) check if the date values are valid
		#	 2) check if date values are both in the past
		now = time.time()
		if time_start > time_end:
			log.error('add_scheduling: end date is smaller than start date')
			raise Exception('INVALID_DATES: end date is smaller than start date')
		if time_start < now and time_end < now:
			log.error('add_scheduling: scheduling is in the past')
			raise Exception('INVALID_DATES: scheduling is in the past')

		# 4) check if there's a colliding scheduling
		#	 ( (time_start1 <= time_start2 <= time_end1) ||
		#	   (time_start1 <= time_end2   <= time_end1) ||
		#	   (time_start2 <= time_start1 <= time_end2) ||
		#	   (time_start2 <= time_end1   <= time_end2) )
		#	 ==> yes, is it
		#	 1) check if colliding scheduling uses same multiplex
		#		==> yes, it does ==> no problem
		#		==> no, it doesn't ==> ERROR
		for scheduling in self.schedulings:
			if ( time_start <= scheduling['time_start'] and scheduling['time_start'] <= time_end ) or \
			   ( time_start <= scheduling['time_end'] and scheduling['time_end'] <= time_end ) or \
			   ( scheduling['time_start'] <= time_start and time_start <= scheduling['time_end'] ) or \
			   ( scheduling['time_start'] <= time_end and time_end <= scheduling['time_end'] ):
				# collision found
				
				if scheduling['multiplex'] != mplex:
					log.error('add_scheduling: colliding scheduling found: %s' % scheduling)
					raise Exception('CONFLICT: colliding scheduling found')

										   
		scheduling = Scheduling(mplex, service_id, target_url, time_start, time_end)
		self.schedulings[ scheduling.id() ] = scheduling

		# 5) calling scheduler now
		yield self.scheduler()

		yield scheduling.id()

	@kaa.coroutine()
	def update_scheduling(self, scheduling_id, target_url, date_start, date_end):
		pass

	@kaa.coroutine()
	def remove_scheduling(self, scheduling_id, force = False):
		pass

	@kaa.coroutine()
	def list_schedulings(self):
		pass

	

@kaa.coroutine()
def main():
	log.setLevel(logging.DEBUG)
	c = Controller( verbose_level = 2 )
	x = (yield c.lsservices())
	print '----------------------------------------'
	x = (yield c.add_scheduling( '2114.0c03.400e', 'file:///data/video/incoming/foo.ts', time.time()+3, time.time()+23 ))
	print 'Scheduling:', x


main()
kaa.main.run()
