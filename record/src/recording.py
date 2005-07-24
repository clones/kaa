import time
import logging

from kaa.notifier import OneShotTimer, Signal

log = logging.getLogger('record')

class Recording(object):
    next_id = 0

    def __init__(self, start, stop, device, channel, output):
        self.start = start
        self.stop = stop
        self.device = device
        self.channel = channel
        self.output = output
        self.id = self.next_id
        self.next_id += 1
        self.timer = { 'start': OneShotTimer(self.__start),
                       'stop': OneShotTimer(self.__stop) }
        self.signals = { 'start': Signal(), 'stop': Signal() }
        self.rec_id = None
        self.schedule()
        
        
    def modify(self, start, stop):
        self.start = start
        self.stop = stop
        self.schedule()


    def remove(self):
        if self.rec_id != None:
            self._stop()
        self.timer['start'].stop()
        self.timer['stop'].stop()

        
    def schedule(self):
        if self.rec_id == None:
            # rec not started yet
            wait = int(max(0, self.start - time.time()))
            log.info('start recording %s in %s seconds' % (self.id, wait))
            self.timer['start'].start(wait * 1000)
        wait = int(max(0, self.stop - time.time()))
        log.info('stop recording %s in %s seconds' % (self.id, wait))
        self.timer['stop'].start(wait * 1000)
            

    def __start(self):
        log.info('start recording %s' % self.id)
        self.rec_id = self.device.start_recording(self.channel, self.output)
        self.signals['start'].emit()

        
    def __stop(self):
        log.info('stop recording %s' % self.id)
        self.device.stop_recording(self.rec_id)
        self.rec_id = None
        self.signals['stop'].emit()
