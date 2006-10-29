import stat
import os
import glob

from kaa import ipc
import kaa.notifier
import kaa.metadata
import kaa.imlib2

from _thumbnailer import epeg_thumbnail, png_thumbnail, fail_thumbnail

jobs = []

class Job(object):
    def __init__(self, id, filename, imagefile, size, update):
        self.client, self.id = id
        self.filename = filename
        self.imagefile = imagefile
        self.size = size
        self.update = update
        

class VideoThumb(object):
    def __init__(self, thumbnailer):
        self._jobs = []
        self._current = None

        self._notify_client = thumbnailer._notify_client
        self._create_failed_image = thumbnailer._create_failed_image

        self.child = kaa.notifier.Process(['mplayer', '-nosound', '-vo', 'png',
                                           '-frames', '8', '-zoom', '-ss' ])
        self.child.signals['completed'].connect(self._completed)
        self.child.signals['stdout'].connect(self._handle_std)
        self.child.signals['stderr'].connect(self._handle_std)


    def append(self, job):
        self._jobs.append(job)
        self._run()

        
    def _handle_std(self, line):
        self._child_std.append(line)


    def _run(self):
        if self.child.is_alive() or not self._jobs or self._current:
            return True
        self._current = self._jobs.pop(0)

        try:
            mminfo = self._current.metadata
            pos = str(int(mminfo.video[0].length / 2.0))
            if hasattr(mminfo, 'type'):
                if mminfo.type in ('MPEG-TS', 'MPEG-PES'):
                    pos = str(int(mminfo.video[0].length / 20.0))
        except:
            # else arbitrary consider that file is 1Mbps and grab position
            # at 10%
            try:
                pos = os.stat(self._current.filename)[stat.ST_SIZE]/1024/1024/10.0
            except (OSError, IOError):
                # send message to client, we are done here
                self._create_failed_image(self._current)
                self._notify_client()
                return
            if pos < 10:
                pos = '10'
            else:
                pos = str(int(pos))
            
        self._child_std = []
        self.child.start([pos, self._current.filename])


    def _completed(self, code):
        # find thumbnails
        captures = glob.glob('000000??.png')
        if not captures:
            # strange, no image files found
            print "error creating capture for %s" % self._current.filename
            for e in self._child_std:
                print e
            self._create_failed_image(self._current)
            self._notify_client(self._current)
            self._current = None
            self._run()
            return

        # scale thumbnail
        width, height = self._current.size
        image = kaa.imlib2.open(captures[-1])
        if image.width > width or image.height > height:
            image = image.scale_preserve_aspect((width,height))
        if image.width * 3 > image.height * 4:
            # fix image with blank bars to be 4:3
            nh = (image.width*3)/4
            ni = kaa.imlib2.new((image.width, nh))
            ni.blend(image, (0,(nh- image.height) / 2))
            image = ni
        elif image.width * 3 < image.height * 4:
            # strange aspect, let's guess it's 4:3
            new_size = (image.width, (image.width*3)/4)
            image = image.scale((new_size))

        # FIXME: use png code to add metadata
        image.save(self._current.imagefile)

        # remove old stuff
        for capture in captures:
            os.remove(capture)

        # notify client and start next video
        self._notify_client(self._current)
        self._current = None
        self._run()
        

    
class Thumbnailer(object):

    def __init__(self, tmpdir):
        self.next_client_id = 0
        self.clients = []
        self._jobs = []
        self._timer = kaa.notifier.Timer(self._run)
        self._ipc = ipc.IPCServer(os.path.join(tmpdir, 'socket'))
        self._ipc.register_object(self, 'thumb')
        self._ipc.signals["client_closed"].connect(self._client_closed)

        # video module
        self.videothumb = VideoThumb(self)
        

    def _notify_client(self, job):
        for id, callback in self.clients:
            if id == job.client:
                callback(job.id, job.filename, job.imagefile,
                         __ipc_oneway=True, __ipc_noproxy_args=True)

        
    def _create_failed_image(self, job):
        dirname = os.path.dirname(os.path.dirname(job.imagefile)) + '/failed/kaa/'
        job.imagefile = dirname + os.path.basename(job.imagefile) + '.png'
        if not os.path.isdir(dirname):
            os.makedirs(dirname, 0700)
        fail_thumbnail(job.filename, job.imagefile)
        return
    
    def _run(self):
        if not self._jobs:
            return False
        
        job = self._jobs.pop(0)

        # FIXME: check if there is already a file and update is False

        if job.filename.lower().endswith('jpg'):
            try:
                epeg_thumbnail(job.filename, job.imagefile + '.jpg', job.size)
                job.imagefile += '.jpg'
                self._notify_client(job)
                return True
            except IOError:
                pass

        try:
            png_thumbnail(job.filename, job.imagefile + '.png', size)
            job.imagefile += '.png'
            self._notify_client(job)
            return True
        except:
            pass
        
        # maybe this is no image
        metadata = kaa.metadata.parse(job.filename)
        if metadata and metadata['media'] == 'video':
            # video file
            print 'video'
            job.metadata = metadata
            self.videothumb.append(job)
            return True

        if metadata and metadata['raw_image']:
            print 'FIXME: store raw data'
            self._create_failed_image(job)
            self._notify_client(job)
            return True
            
        # broken file
        self._create_failed_image(job)
        self._notify_client(job)
        return True

    
    def connect(self, callback):
        self.next_client_id += 1
        self.clients.append((self.next_client_id, callback))
        return self.next_client_id


    def thumbnail(self, id, filename, imagefile, size, update=True):

        self._jobs.append(Job(id, filename, imagefile, size, update))
        if not self._timer.active():
            self._timer.start(0.001)

    
    def _client_closed(self, client):
        for client_info in self.clients[:]:
            id, c = client_info
            if ipc.get_ipc_from_proxy(c) == client:
                print 'found'
                for j in self._jobs[:]:
                    if j.client == id:
                        print 'rm', j
                        self._jobs.remove(j)
                for j in self.videothumb._jobs[:]:
                    if j.client == id:
                        print 'rm', j
                        self.videothumb._jobs.remove(j)
                self.clients.remove(client_info)
                return

tmpdir = os.path.join(kaa.TEMP, 'thumb')
if not os.path.isdir(tmpdir):
    os.mkdir(tmpdir)
os.chdir(tmpdir)

Thumbnailer(tmpdir)
kaa.notifier.loop()
