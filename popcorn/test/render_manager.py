# Rendering manager: renders one or more videos to a canvas.  Video info is
# delivered via fifo by a protocol that's currently implemented in kaa.xine
# and mplayer vo_export patch (in patches/).
#
# This script takes as arguments one or more fifos to monitor for frame
# notifications.  Each fifo is a separate video source.  E.g.:
# 
#   mkfifo /tmp/fifo1 /tmp/fifo2 /tmp/fifo3
#   python render_manager.py /tmp/fifo*
#
# This is heavily WIP.  Will document later.

import os, struct, time
import kaa.display, kaa.evas, kaa.shm, kaa, kaa.input.stdin, sys

# Default window size.
WIN_SIZE = 640, 480
#WIN_SIZE = 1600, 1200
#WIN_SIZE = 1920, 1080

# Use hardware yuv2rgb conversion?
HARDWARE_CONV = True

class Manager:
    def __init__(self, evas_window):
        self._window = evas_window
        self._evas = evas_window.get_evas()
        self._videos = []
        self._current = None
        self._render_needed = False
        self._selecting = False
        self.signals = { 'render': kaa.notifier.Signal() }

    def add_video(self, video):
        self._videos.append(video)
        self._fit_window()

    def remove_video(self, video):
        self._videos.remove(video)
        self._fit_window()
        if len(self._videos) == 0:
            self._window.hide()
        if self._current == video:
            self._current = None

    def get_videos(self):
        return self._videos

    def next_video(self):
        if not self._current:
            cur = 0
        else:
            cur = self._videos.index(self._current)

        for idx in range(cur+1, len(self._videos)) + range(0, cur+1):
            if self._videos[idx]._shmem:
                self._current = self._videos[idx]
                break
        else:
            self._current = None
        self._selecting = True
        return self._current

    def get_selecting(self):
        return self._selecting

    def set_selecting(self, value):
        self._selecting = value

    def get_current(self):
        return self._current

    def queue_render(self):
        self._render_needed = True

    def render(self):
        if not self._render_needed:
            return

        t0=time.time()
        self._evas.render()
        self.signals['render'].emit()
        #print "Render:", time.time()-t0
        self._render_needed = False


    def _fit_window(self):
        if len(self._videos) != 1:
            return
        if not self._videos[0]._fit_canvas:
            size = self._videos[0].geometry_get()[1]
            self._window.resize(size)
        self._window.show()
    

class Video(kaa.evas.Image):
    def __init__(self, evas, fifo_fname, manager):
        super(Video, self).__init__(evas)

        self._manager = manager
        self._fifo_fname = fifo_fname
        self._aspect = 1.0
        self._shmem = None
        self._fit_canvas = True
        self._last_width = None

        self._setup_fifo()

    def _setup_fifo(self):
        if isinstance(self._fifo_fname, int):
            fifo = self._fifo_fname
        else:
            fifo = os.open(self._fifo_fname, os.O_RDONLY | os.O_NONBLOCK)
            try:
                while len(os.read(fifo, 4096)) != 0:
                    # Consume any pending frame notifications that might be
                    # buffered in the fifo
                    pass
            except OSError:
                pass

        print "Setup fifo", fifo
        kaa.notifier.WeakSocketDispatcher(self._new_frame, fifo).register(fifo)


    def _new_frame(self, fifo):
        t0=time.time()
        header = os.read(fifo, 16)
        
        if len(header) == 0:
            self._setup_fifo()
            os.close(fifo)
            return False

        shmid, offset = struct.unpack("II8x", header)
        if self._shmem and self._shmem.shmid != shmid:
            self._shmem.detach()
            self._shmem = None

        if not self._shmem:
            try:
                self._shmem = kaa.shm.memory(shmid)
            except kaa.shm.error:
                print "Couldn't attach to shmem segment"
                return False
            self._shmem.attach()
            self.object_raise()

        header = self._shmem.read(32, offset)
        lock, width, height, stride, aspect = struct.unpack("bHHHd16x", header)
        #print "Newframe", len(header), shmid, offset, lock, width, height, stride, aspect
        if self.size_get() != (stride, height) or aspect != self._aspect:
            self._aspect = aspect
            self.data_set(0, False)
            # Bug in evas GL engine when text width != stride, so we must make
            # the image width the stride and crop after.
            self.size_set((stride, height))
            if self._fit_canvas:
                self.resize(self.evas_get().output_size_get())
            elif not self._last_width:
                self.resize((int(height * aspect), 0))
            else:
                # Keep last width, correct for new aspect
                cur_width = self.geometry_get()[1][0]
                self.resize((cur_width, 0))

            # TODO: crop to width

        t1=time.time()
        if HARDWARE_CONV:
            self.data_set(self._shmem.addr + offset + 32, False, stride = stride)
        else:
            self.pixels_import(self._shmem.addr + offset + 32, width, height, kaa.evas.PIXEL_FORMAT_YUV420P_601, stride)
        self.pixels_dirty_set()
        self._manager.queue_render()
        self._manager.signals['render'].connect_once(lambda: self._shmem.write('\x00', offset))
        t2 = time.time()
        #print "Timing: header=%0.5f evas=%0.5f total=%0.5f" % (t1-t0, t2-t1, t2-t0)

    def resize(self, (w, h)):
        h = int(w / self._aspect)
        self.fill_set((0, 0), (w, h))
        super(Video, self).resize((w, h))
        if self._fit_canvas:
            self.center()
        self._last_width = w

    def center(self):
        canvas_w, canvas_h = self.evas_get().output_size_get()
        w, h = self.geometry_get()[1]
        self.move(((canvas_w - w) / 2, (canvas_h - h) / 2))

    def set_fit(self, value):
        if value == self._fit_canvas:
            return
        self._fit_canvas = value
        if value or not self._last_width:
            self.resize(self.evas_get().output_size_get())
        else:
            self.resize((self._last_width, -1))

    def get_fit(self):
        return self._fit_canvas


def resize_window(last, size, canvas, bg):
    canvas.output_size_set(size)
    canvas.viewport_set((0, 0), size)
    bg.resize(size)
    for video in manager.get_videos():
        if video.get_fit():
            video.resize(size)


def key(code):
    video = manager.get_current()
    if video:
        r, g, b, a = video.color_get()
        (x, y), (w, h) = video.geometry_get()

    if code == 'q':
        sys.exit(0)
    elif code == 'F':
        win.set_fullscreen(not win.get_fullscreen())

    elif code == 'space':
        if manager.get_selecting():
            if video:
                video.color_set(255, 255, 255, a)
            manager.set_selecting(False)
        else:
            manager.set_selecting(True)
            video = manager.get_current()
            if not video:
                video = manager.next_video()
            if video:
                video.color_set(255, 192, 192, video.color_get()[3])

    elif code == 'tab':
        if video:
            video.color_set(255, 255, 255, a)
        video = manager.next_video()
        if video:
            video.object_raise()
            video.color_set(255, 192, 192, video.color_get()[3])

    if not video or not manager.get_selecting():
        print "No video selected, hit tab"
        return

    if code == ']':
        video.resize((w + 4, -1))
    elif code == '[':
        video.resize((w - 4, -1))
    elif code == 'up':
        video.move((x, y - 4))
        video.set_fit(False)
    elif code == 'down':
        video.move((x, y + 4))
        video.set_fit(False)
    elif code == 'left':
        video.move((x - 4, y))
        video.set_fit(False)
    elif code == 'right':
        video.move((x + 4, y))
        video.set_fit(False)

    elif code == 'a':
        video.color_set(r, g, b, a - 5)
    elif code == 'A':
        video.color_set(r, g, b, a + 5)
    elif code == 'h':
        video.hide()
    elif code == 's':
        video.show()
    elif code == 'f':
        video.set_fit(not video.get_fit())


if __name__ == '__main__':
    win = kaa.display.EvasX11Window(gl = True, size = WIN_SIZE)
    manager = Manager(win)
    e = win.get_evas()

    bg = e.object_rectangle_add()
    bg.color_set(0,0,0,255)
    bg.resize(WIN_SIZE)
    bg.show()

    for fifo in sys.argv[1:]:
        video = Video(e, fifo, manager)
        if HARDWARE_CONV:
            video.colorspace_set(kaa.evas.COLORSPACE_YCBCR422P601_PL)
        video.show()
        manager.add_video(video)

    img = e.object_image_add('data/music.png')
    img.color_set(255,255,255,120)
    img.layer_set(10)
    img.show()

    e.render()

    kaa.signals['step'].connect(manager.render)
    kaa.signals['stdin_key_press_event'].connect(key)
    win.signals['key_press_event'].connect(key)
    win.signals['resize_event'].connect(resize_window, e, bg)
    #win.set_fullscreen(True)

    print "Keys: q, arrows, tab, space, F, f, a, A, [, ], h, s"
    kaa.main()
