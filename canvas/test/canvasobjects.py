import shm, md5, re, time

import kaa
from kaa import canvas, evas

# Test code for vf_overlay (MPlayerOSDCanvas) and vf_outbuf (CanvasMovie) 
# patches for MPlayer.  Eventually these classes will be tidied up and
# rolled into kaa.canvas.

class MPlayerOSDCanvas(canvas.BufferCanvas):
    BUFFER_UNLOCKED = 0x10
    BUFFER_LOCKED = 0x20

    def __init__(self, mp):
        super(MPlayerOSDCanvas, self).__init__()
        self._shmem = None
        self._mp = mp
        
        assert(self._mp.get_state() == "exited")
        self._mp.append_filter("overlay=%s" % self._get_shm_key())
        self._mp.signals["output"].connect_weak(self._handle_mplayer_line)

        # Our initial state is alpha=255, visible=0
        self._osd_alpha = self._mp_alpha = 255
        self._mp_visible = 0
        self.hide()

    def __del__(self):
        if self._shmem and self._shmem.attached:
            self._shmem.detach()

    def get_mplayer(self):
        return self._mp

    def _handle_mplayer_line(self, line):
        if line[:8] == "overlay:" and line.find("reusing") == -1:
            m = re.search("(\d+)x(\d+)", line)
            if m:
                osd_size = int(m.group(1)), int(m.group(2))
                self._setup(osd_size)

    def _get_shm_key(self):
        name = "mplayer-overlay.%s" % self.get_mplayer().get_instance_id()
        return int(md5.md5(name).hexdigest()[:7], 16)

    def _setup(self, size):
        self._size = w, h = size
        self._shmem = shm.memory(shm.getshmid(self._get_shm_key()))
        self._shmem.attach()
        self.create(size, self._shmem.addr+16)
        print "OSD canvas created: w=%d h=%d" % (w, h)

    def _check_render_queued(self):
        #print "Check render queued, lock =", self._is_lock(MPlayerOSDCanvas.BUFFER_LOCKED)
        if self._is_lock(MPlayerOSDCanvas.BUFFER_LOCKED):
            return

        return super(MPlayerOSDCanvas, self)._check_render_queued()
 
    def _is_lock(self, byte):
        try:
            return self._shmem and ord(self._shmem.read(1)) == byte
        except shm.error:
            self._shmem = None
            return False

    def _set_lock(self, byte):
        if self._shmem and self._shmem.attached:
            self._shmem.write(chr(byte))

    def render(self):
        regions = super(MPlayerOSDCanvas, self).render()

        if len(regions) == 0 and self["visible"] == self._mp_visible and self._osd_alpha == self._mp_alpha:
            return

        #print "UPDATED CANVAS WITH REGIONS", regions, "alpha=%d visible=%d" % (self._osd_alpha, self["visible"])
        cmd = ["visible=%d" % self["visible"], "alpha=%d" % self._osd_alpha]
        if len(regions):
            for (x, y, w, h) in regions:
                cmd.append("invalidate=%d:%d:%d:%d" % (x, y, w, h))
        self.get_mplayer()._slave_cmd("overlay %s" %  ",".join(cmd))
        self._set_lock(MPlayerOSDCanvas.BUFFER_LOCKED)
        self._mp_alpha = self._osd_alpha
        self._mp_visible = self["visible"]


    def _set_property_color(self, color):
        if None in color:
            color = tuple(map(lambda x, y: (x,y)[x==None], color, self["color"]))
        r, g, b, a = color
        # vf_overlay does not support color filters, only alpha.
        assert(r == g == b == 255)
        # 0 <= alpha < = 255
        a = max(0, min(255, a))
        if hasattr(self, "_osd_alpha") and self._osd_alpha != a:
            # If the alpha set here is different than the vf_overlay alpha,
            # then we need to queue a render.
            self._osd_alpha = a
            self._queue_render()

        # But tell the lower canvas objects we're still fully opaque,
        # otherwise our children will get blended to the new alpha by
        # evas, which is unnecessary since vf_overlay supports global
        # alpha.
        super(MPlayerOSDCanvas, self)._set_property_color((255,255,255,255))

    def get_color(self):
        return (255, 255, 255, self._osd_alpha)


class CanvasMovie(canvas.CanvasImage):

    BUFFER_UNLOCKED = 0x00
    BUFFER_LOCKED = 0xf0
    BUFFER_SCALED = 0x01

    def __init__(self, mp):
        super(CanvasMovie, self).__init__()
        self._shmem = None
        self._mp = mp
        self._waiting_for_render = False

        assert(self._mp.get_state() == "exited")
        self._mp.prepend_filter("outbuf=%d:0:yv12" % self._get_shm_key())
        self._mp.signals["start"].connect_weak(self._setup)

        self.set_has_alpha(False)


    def __del__(self):
        if self._shmem and self._shmem.attached:
            self._shmem.detach()

    def _get_shm_key(self):
        name = "mplayer-frame.%s" % self.get_mplayer().get_instance_id()
        return int(md5.md5(name).hexdigest()[:7], 16)

    def get_mplayer(self):
        return self._mp

    def _canvased(self, canvas):
        super(CanvasMovie, self)._canvased(canvas)
        self._setup()

    def _setup(self):
        if not self.get_canvas().get_evas() or self.get_mplayer().get_state() != "playing":
            # Canvas isn't ready yet.
            return False

        info = self.get_mplayer().get_file_info()
        w, h = info["width"], info["height"]

        self._shmem = shm.memory(shm.getshmid(self._get_shm_key()))
        self._shmem.attach()

        if self["size"] == (-1, -1):
            self._o.size_set((w, h))
            self._o.resize((w, h))
            self._o.fill_set((0, 0), (w, h))

        self.get_mplayer()._slave_cmd("outbuf 2")
        kaa.notifier.WeakTimer(self._check_frame_pending).start(0.01)

    def _sync(self, regions):
        try:
            self._shmem.write(chr(CanvasMovie.BUFFER_UNLOCKED))
            self._waiting_for_render = False
        except:
            self._shmem = None

    def _sync_property_size(self):
        if self.get_mplayer().get_state() != "playing":
            return False

        info = self.get_mplayer().get_file_info()
        w, h = self["size"]
        aspect = info["aspect"]
        if w == h == -1:
            w, h = self.get_mplayer().get_vo_size()
        elif w == -1:
            w = int(h * aspect) & ~1
        elif h == -1:
            h = int(w / aspect) & ~1

        # Use mplayer to scale the video if the area is smaller.
        mpi_w, mpi_h = info["width"], info["height"]
        if w * h < mpi_w * mpi_h and w % 2 == 0:
            self.get_mplayer()._slave_cmd("outbuf 2 %d %d" % (w, h))

        if (w, h) != self["size"]:
            self._properties["size"] = w, h

        super(CanvasMovie, self)._sync_property_size()


    def _check_frame_pending(self):
        try:
            lockbyte = ord(self._shmem.read(1))
        except (shm.error, AttributeError):
            self._shmem = None
            return False

        if not (lockbyte & CanvasMovie.BUFFER_LOCKED) or self._waiting_for_render:
            return

        # TODO: if any ancestor (including canvas) is hidden, no sense in
        # updating; just unlock the buffer immediately.

        if lockbyte & CanvasMovie.BUFFER_SCALED:
            self._o.size_set(self["size"])

        w, h = self._o.size_get()
        #print "HAVE FRAME", w, h, time.time()
        self._o.pixels_import(self._shmem.addr + 16, w, h, evas.PIXEL_FORMAT_YUV420P_601)
        self._o.pixels_dirty_set()
        self._queue_render()
        self.get_canvas().signals["updated"].connect_once(self._sync)
        self._waiting_for_render = True
