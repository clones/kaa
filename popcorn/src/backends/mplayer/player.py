import os, re, string, tempfile, time, stat, threading, md5, struct
from kaa import notifier, display, shm
import kaa
import kaa.utils
from kaa.popcorn.backends.base import MediaPlayer
from kaa.popcorn.ptypes import *
from kaa.popcorn.utils import parse_mrl

# 0 = none, 1 = interesting lines, 2 = everything, 3 = everything + status,
# 4 = everything + status + run through gdb
DEBUG=1

BUFFER_UNLOCKED = 0x10
BUFFER_LOCKED = 0x20


# A cache holding values specific to an MPlayer executable (version,
# filter list, video/audio driver list, input keylist).  This dict is
# keyed on the full path of the MPlayer binary.
_cache = {}

def _get_mplayer_info(path, callback = None, mtime = None):
    """
    Fetches info about the given MPlayer executable.  If the values are
    cached and the cache is fresh, it returns a dict immediately.  If it
    needs to load MPlayer to fetch the values and callback is specified,
    it does so in a thread, and calls callback with the results on
    completion.  If callback is None and no information is in the cache,
    this function blocks.

    If 'mtime' is not None, it means we've called ourself as a thread.
    """

    if not mtime:
        # Fetch the mtime of the binary
        try:
            mtime = os.stat(path)[stat.ST_MTIME]
        except (OSError, TypeError):
            return None

        if path in _cache and _cache[path]["mtime"] == mtime:
            # Cache isn't stale, so return that.
            return _cache[path]

        if callback:
            # We need to run MPlayer to get these values.  Create a signal, call
            # ourself as a thread, and return the signal back to the caller.
            thread = notifier.Thread(_get_mplayer_info, path, None, mtime)
            # Thread class ensures the callbacks get invoked in the main thread.
            thread.signals["completed"].connect(callback)
            thread.signals["exception"].connect(callback)
            thread.start()
            return None

    # At this point we're running in a thread.

    info = {
        "version": None,
        "mtime": mtime,
        "video_filters": {},
        "video_drivers": {},
        "audio_filters": {},
        "audio_drivers": {},
        "keylist": []
    }

    regexps = (
        ("video_filters", "-vf help", "\s*(\w+)\s+:\s+(.*)"),
        ("video_drivers", "-vo help", "\s*(\w+)\s+(.*)"),
        ("audio_filters", "-af help", "\s*(\w+)\s+:\s+(.*)"),
        ("audio_drivers", "-ao help", "\s*(\w+)\s+(.*)"),
        ("keylist", "-input keylist", "^(\w+)$"),
    )

    for key, args, regexp in regexps:
        for line in os.popen("%s %s" % (path, args)):
            # Check version
            if line.startswith("MPlayer "):
                info["version"] = line.split()[1]

            # Check regexp
            m = re.match(regexp, line.strip())
            if not m:
                continue

            if len(m.groups()) == 2:
                info[key][m.group(1)] = m.group(2)
            else:
                info[key].append(m.group(1))

    _cache[path] = info
    return info



class MPlayerError(Exception):
    pass

class MPlayerExitError(MPlayerError):
    pass

class MPlayer(MediaPlayer):

    PATH = None
    _instance_count = 0

    RE_STATUS = re.compile("V:\s*([\d+\.]+)|A:\s*([\d+\.]+)\s\W")

    def __init__(self):
        super(MPlayer, self).__init__()
        self._mp_cmd = MPlayer.PATH
        if not self._mp_cmd:
            self._mp_cmd = kaa.utils.which("mplayer")

        if not self._mp_cmd:
            raise MPlayerError, "No MPlayer executable found in PATH"

        self._debug = DEBUG
        # Used for vf_overlay and vf_outbuf
        self._instance_id = "%d-%d" % (os.getpid(), MPlayer._instance_count)
        MPlayer._instance_count += 1

        self._process = None
        self._state = STATE_NOT_RUNNING
        self._overlay_shmem = None
        self._outbuf_shmem = None
        self._file = None
        self._file_args = []

        self._file_info = {}
        self._position = 0.0
        self._filters_pre = []
        self._filters_add = []
        self._last_line = None

        self.signals.update({
            "output": notifier.Signal(),
        })

        self._mp_info = _get_mplayer_info(self._mp_cmd, self._handle_mp_info)
        self._check_new_frame_timer = notifier.WeakTimer(self._check_new_frame)
        self._cur_outbuf_mode = [True, False, None] # vo, shmem, size


    def __del__(self):
        if self._outbuf_shmem:
            self._outbuf_shmem.detach()
        if self._overlay_shmem:
            self._overlay_shmem.detach()


    def _spawn(self, args, hook_notifier = True):
        if self._debug > 0:
            print "Spawn:", self._mp_cmd, args

        if self._debug > 3:
            # With debug > 3, run mplayer through gdb.
            self._process = notifier.Process("gdb")
            self._process.start(self._mp_cmd)
            self._process.write("run %s\n" % args)
        else:
            self._process = notifier.Process(self._mp_cmd)
            self._process.start(args)

        if hook_notifier:
            self._process.signals["stdout"].connect_weak(self._handle_line)
            self._process.signals["stderr"].connect_weak(self._handle_line)
            self._process.signals["completed"].connect_weak(self._exited)
            self._process.set_stop_command(notifier.WeakCallback(self._end_child))
        return self._process


    def _make_dummy_input_config(self):
        """
        There is no way to make MPlayer ignore keys from the X11 window.  So
        this hack makes a temp input file that maps all keys to a dummy (and
        non-existent) command which causes MPlayer not to react to any key
        presses, allowing us to implement our own handlers.  The temp file is
        deleted once MPlayer has read it.
        """
        keys = filter(lambda x: x not in string.whitespace, string.printable)
        keys = list(keys) + self._mp_info["keylist"]
        fp, filename = tempfile.mkstemp()
        for key in keys:
            os.write(fp, "%s noop\n" % key)
        os.close(fp)
        return filename


    def _handle_mp_info(self, info):
        if isinstance(info, Exception):
            self._state = STATE_NOT_RUNNING
            # TODO: handle me
            raise info
        self._mp_info = info


    def _handle_line(self, line):
        if self._debug:
            if re.search("@@@|outbuf|overlay", line, re.I) and self._debug == 1:
                print line
            elif line[:2] not in ("A:", "V:") and self._debug == 2:
                print line
            elif self._debug == 3:
                print line

        if line.startswith("V:") or line.startswith("A:"):
            m = MPlayer.RE_STATUS.search(line)
            if m:
                old_pos = self._position
                self._position = float((m.group(1) or m.group(2)).replace(",", "."))
                if self._position - old_pos < 0 or self._position - old_pos > 1:
                    self.signals["seek"].emit(self._position)

                # XXX this logic won't work with seek-while-paused patch; state
                # will be "playing" after a seek.
                if self._state == STATE_PAUSED:
                    self.signals["pause_toggle"].emit()
                if self._state not in (STATE_PAUSED, STATE_PLAYING):
                    self.set_frame_output_mode()
                    self._state = STATE_PLAYING
                    self.signals["stream_changed"].emit()
                elif self._state != STATE_PLAYING:
                    self._state = STATE_PLAYING
                    self.signals["play"].emit()

        elif line.startswith("  =====  PAUSE"):
            self._state = STATE_PAUSED
            self.signals["pause_toggle"].emit()
            self.signals["pause"].emit()

        elif line.startswith("ID_") and line.find("=") != -1:
            attr, value = line.split("=")
            attr = attr[3:]
            info = { "VIDEO_FORMAT": ("vfourcc", str),
                     "VIDEO_BITRATE": ("vbitrate", int),
                     "VIDEO_WIDTH": ("width", int),
                     "VIDEO_HEIGHT": ("height", int),
                     "VIDEO_FPS": ("fps", float),
                     "VIDEO_ASPECT": ("aspect", float),
                     "AUDIO_FORMAT": ("afourcc", str),
                     "AUDIO_CODEC": ("acodec", str),
                     "AUDIO_BITRATE": ("abitrate", int),
                     "LENGTH": ("length", float),
                     "FILENAME": ("filename", str) }
            if attr in info:
                self._file_info[info[attr][0]] = info[attr][1](value)

        elif line.startswith("Movie-Aspect"):
            aspect = line[16:].split(":")[0].replace(",", ".")
            if aspect[0].isdigit():
                self._file_info["aspect"] = float(aspect)

        elif line.startswith("VO:"):
            m = re.search("=> (\d+)x(\d+)", line)
            if m:
                vo_w, vo_h = int(m.group(1)), int(m.group(2))
                if "aspect" not in self._file_info or self._file_info["aspect"] == 0:
                    # No aspect defined, so base it on vo size.
                    self._file_info["aspect"] = vo_w / float(vo_h)

        elif line.startswith("overlay:") and line.find("reusing") == -1:
            m = re.search("(\d+)x(\d+)", line)
            if m:
                width, height = int(m.group(1)), int(m.group(2))
                try:
                    if self._overlay_shmem:
                        self._overlay_shmem.detach()
                except shm.error:
                    pass
                self._overlay_shmem = shm.memory(shm.getshmid(self._get_overlay_shm_key()))
                self._overlay_shmem.attach()

                self.signals["osd_configure"].emit(width, height, self._overlay_shmem.addr + 16,
                                                   width, height)

        elif line.startswith("outbuf:") and line.find("shmem key") != -1:
            try:
                if self._outbuf_shmem:
                    self._outbuf_shmem.detach()
            except shm.error:
                pass
            self._outbuf_shmem = shm.memory(shm.getshmid(self._get_outbuf_shm_key()))
            self._outbuf_shmem.attach()
            self.set_frame_output_mode()  # Sync

        elif line.startswith("EOF code"):
            if self._state in (STATE_PLAYING, STATE_PAUSED):
                self._state = STATE_IDLE

        elif line.startswith("Parsing input"):
            # Delete the temporary key input file.
            file = line[line.find("file")+5:]
            os.unlink(file)

        #elif line.startswith("File not found"):
        #    file = line[line.find(":")+2:]
        #    raise IOError, (2, "No such file or directory: %s" % file)

        elif line.startswith("FATAL:"):
            raise MPlayerError, line.strip()

        elif self._debug > 3 and line.startswith("Program received signal SIGSEGV"):
            # Mplayer crashed, issue backtrace.
            self._process.write("thread apply all bt\n")

        if line.strip():
            self.signals["output"].emit(line)
            self._last_line = line


    def _get_overlay_shm_key(self):
        name = "mplayer-overlay.%s" % self._instance_id
        return int(md5.md5(name).hexdigest()[:7], 16)

    def _get_outbuf_shm_key(self):
        name = "mplayer-outbuf.%s" % self._instance_id
        return int(md5.md5(name).hexdigest()[:7], 16)


    def _slave_cmd(self, cmd):
        if not self.is_alive():
            return False

        if self._debug >= 1:
            print "SLAVE:", cmd
        self._process.write(cmd + "\n")


    def _exited(self, exitcode):
        self._state = STATE_NOT_RUNNING
        # exit code is strange somehow
        # if exitcode != 0:
        #     raise MPlayerExitError, (exitcode, self._last_line)


    def is_alive(self):
        return self._process and self._process.is_alive()

    def open(self, mrl, user_args = None):

        if self.get_state() != STATE_NOT_RUNNING:
            print 'Error: not idle'
            return False

        schemes = self.get_supported_schemes()
        scheme, path = parse_mrl(mrl)

        if scheme not in schemes:
            raise ValueError, "Unsupported mrl scheme '%s'" % scheme

        self._file_args = []
        if scheme in ("file", "fifo"):
            self._file = path
        elif scheme == "dvd":
            file, title = re.search("(.*?)(\/\d+)?$", path).groups()
            if file not in ("/", "//"):
                if not os.path.isfile(file):
                    raise ValueError, "Invalid ISO file: %s" % file
                self._file_args.append("-dvd-device \"%s\"" % file)

            self._file = "dvd://"
            if title:
                self._file += title[1:]
        else:
            self._file = mrl

        if user_args:
            self._file_args.append(user_args)


    def play(self):
        # we know that self._mp_info has to be there or the object would
        # not be selected by the generic one. FIXME: verify that!
        assert(self._mp_info)

        keyfile = self._make_dummy_input_config()

        filters = self._filters_pre[:]
        if 'outbuf' in self._mp_info['video_filters']:
            filters += ["outbuf=%s:yv12" % self._get_outbuf_shm_key()]

        filters += ["scale=%d:-2" % self._size[0], "expand=%d:%d" % self._size,
                    "dsize=%d:%d" % self._size ]

        # FIXME: check freevo filter list and add stuff like pp

        filters += self._filters_add
        if 'overlay' in self._mp_info['video_filters']:
            filters += ["overlay=%s" % self._get_overlay_shm_key()]

        args = [ "-v", "-slave", "-osdlevel", "0", "-nolirc", "-nojoystick", \
                 "-nomouseinput", "-nodouble", "-fixed-vo", "-identify", \
                 "-framedrop", "-vf", ",".join(filters) ]

        if isinstance(self._window, display.X11Window):
            args.extend((
                "-wid", hex(self._window.get_id()),
                "-display", self._window.get_display().get_string(),
                "-input", "conf=%s" % keyfile))

        if self._file_args:
            if isinstance(self._file_args, str):
                args.extend(self._file_args.split(' '))
            else:
                args.extend(self._file_args)

        if self._file:
            args.append(self._file)

        self._spawn(args)
        self._state = STATE_OPENING

        return


    def pause(self):
        if self.get_state() == STATE_PLAYING:
            self._slave_cmd("pause")


    def resume(self):
        if self.get_state() == STATE_PAUSED:
            self._slave_cmd("pause")

    def seek(self, value, type):
        s = [SEEK_RELATIVE, SEEK_PERCENTAGE, SEEK_ABSOLUTE]
        self._slave_cmd("seek %f %s" % (value, s.index(type)))

    def stop(self):
        self.die()
        self._state = STATE_SHUTDOWN

    def _end_child(self):
        self._slave_cmd("quit")
        # Could be paused, try sending again.
        self._slave_cmd("quit")

    def die(self):
        if self._process:
            self._process.stop()

    def get_position(self):
        return self._position

    def get_info(self):
        return self._file_info

    def prepend_filter(self, filter):
        self._filters_pre.append(filter)

    def append_filter(self, filter):
        self._filters_add.append(filter)

    def get_filters(self):
        return self._filters_pre + self._filters_add

    def remove_filter(self, filter):
        for l in (self._filters_pre, self._filters_add):
            if filter in l:
                l.remove(filter)

    def osd_update(self, alpha = None, visible = None, invalid_regions = None):
        cmd = []
        if alpha != None:
            cmd.append("alpha=%d" % alpha)
        if visible != None:
            cmd.append("visible=%d" % int(visible))
        if invalid_regions:
            for (x, y, w, h) in invalid_regions:
                cmd.append("invalidate=%d:%d:%d:%d" % (x, y, w, h))
        self._slave_cmd("overlay %s" % ",".join(cmd))
        self._overlay_set_lock(BUFFER_LOCKED)


    def osd_can_update(self):
        if not self._overlay_shmem:
            return False

        try:
            if ord(self._overlay_shmem.read(1)) == BUFFER_UNLOCKED:
                return True
        except shm.error:
            self._overlay_shmem.detach()
            self._overlay_shmem = None

        return False


    def _overlay_set_lock(self, byte):
        try:
            if self._overlay_shmem and self._overlay_shmem.attached:
                self._overlay_shmem.write(chr(byte))
        except shm.error:
            self._overlay_shmem.detach()
            self._overlay_shmem = None


    def _check_new_frame(self):
        if not self._outbuf_shmem:
            return

        try:
            lock, width, height, aspect = struct.unpack("hhhd", self._outbuf_shmem.read(16))
        except shm.error:
            self._outbuf_shmem.detach()
            self._outbuf_shmem = None
            return

        if lock & BUFFER_UNLOCKED:
            return

        if width > 0 and height > 0 and aspect > 0:
            self.signals["frame"].emit(width, height, aspect, self._outbuf_shmem.addr + 16, "yv12")

    def unlock_frame_buffer(self):
        try:
            self._outbuf_shmem.write(chr(BUFFER_UNLOCKED))
        except shm.error:
            self._outbuf_shmem.detach()
            self._outbuf_shmem = None


    def set_frame_output_mode(self, vo = None, notify = None, size = None):
        if vo != None:
            self._cur_outbuf_mode[0] = vo
        if notify != None:
            self._cur_outbuf_mode[1] = notify
            if notify:
                self._check_new_frame_timer.start(0.01)
            else:
                self._check_new_frame_timer.stop()
        if size != None:
            self._cur_outbuf_mode[2] = size

        if not self.is_alive():
            return

        mode = { (False, False): 0, (True, False): 1,
                 (False, True): 2, (True, True): 3 }[tuple(self._cur_outbuf_mode[:2])]

        size = self._cur_outbuf_mode[2]
        if size == None:
            self._slave_cmd("outbuf %d" % mode)
        else:
            self._slave_cmd("outbuf %d %d %d" % (mode, size[0], size[1]))

    def nav_command(self, input):
        # MPlayer has no dvdnav support (yet).
        return False
