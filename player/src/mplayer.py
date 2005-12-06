import os, re, string, tempfile, time, stat, threading, md5, shm
from kaa import notifier, display
import kaa
from base import *

# 0 = none, 1 = interesting lines, 2 = everything, 3 = everything + status
DEBUG=1

# A cache holding values specific to an MPlayer executable (version,
# filter list, video/audio driver list, input keylist).  This dict is
# keyed on the full path of the MPlayer binary.
_cache = {}

def _get_mplayer_info(path, callback, mtime = None):
    """
    Fetches info about the given MPlayer executable.  If the values are
    cached and the cache is fresh, it returns a dict immediately.  If it
    needs to load MPlayer to fetch the values, it returns a Signal object
    that the caller can connect to to receive the result once it's complete.
    The value passed to the signal callback is either the values dict, or an
    Exception object if an error occurred.

    If 'mtime' is not None, it means we've called ourself as a thread.
    """

    if not mtime:
        # Fetch the mtime of the binary
        mtime = os.stat(path)[stat.ST_MTIME]

        if path in _cache and _cache[path]["mtime"] == mtime:
            # Cache isn't stale, so return that.
            return _cache[path]

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

    OVERLAY_BUFFER_UNLOCKED = 0x10
    OVERLAY_BUFFER_LOCKED = 0x20


    RE_STATUS = re.compile("V:\s*([\d+\.]+)|A:\s*([\d+\.]+)\s\W")

    def __init__(self):
        super(MPlayer, self).__init__()
        self._mp_cmd = MPlayer.PATH
        if not self._mp_cmd:
            for dir in os.getenv("PATH").split(":"):
                cmd = os.path.join(dir, "mplayer")
                if os.path.exists(cmd):
                    self._mp_cmd = cmd
                    break

        if not self._mp_cmd:
            raise MPlayerError, "No MPlayer executable found in PATH"

        self._debug = DEBUG
        # Used for vf_overlay and vf_outbuf
        self._instance_id = "%d-%d" % (os.getpid(), MPlayer._instance_count)
        MPlayer._instance_count += 1

        # Size of the window as reported by MPlayer (aspect-corrected)
        self._vo_size = None 
        self._process = None
        self._state = STATE_NOT_RUNNING
        self._state_data = None
        self._overlay_shmem = None
        self._outbuf_shmem = None

        self._file_info = {}
        self._position = 0.0
        self._eat_ticks = 0
        self._filters_pre = []
        self._filters_add = []
        self._last_line = None
        
        self.signals.update({
            "output": notifier.Signal(),
        })

        self._mp_info = _get_mplayer_info(self._mp_cmd, self._handle_mp_info)


    def _spawn(self, args, hook_notifier = True):
        self._process = notifier.Process(self._mp_cmd)
        self._process.start(args)
        if hook_notifier:
            self._process.signals["stdout"].connect_weak(self._handle_line)
            self._process.signals["stderr"].connect_weak(self._handle_line)
            self._process.signals["completed"].connect_weak(self._exited)
            self._process.set_stop_command(self.stop)
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
        if self._state_data:
            file, user_args = self._state_data
            self._state_data = None
            self._start(file, user_args)


    def _handle_line(self, line):
        if line.startswith("V:") or line.startswith("A:"):
            m = MPlayer.RE_STATUS.search(line)
            if m:
                old_pos = self._position
                self._position = float((m.group(1) or m.group(2)).replace(",", "."))
                if self._position - old_pos < 0 or self._position - old_pos > 1:
                    self.signals["seek"].emit(self._position)

                if self._eat_ticks > 0:
                    self._eat_ticks -= 1
                #else:
                #    self.signals["tick"].emit(self._position)

                # XXX this logic won't work with seek-while-paused patch; state
                # will be "playing" after a seek.
                if self._state == STATE_PAUSED:
                    self.signals["pause_toggle"].emit()
                if self._state not in (STATE_PAUSED, STATE_PLAYING):
                    self._state = STATE_PLAYING
                    self.signals["start"].emit()
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
                self._vo_size = vo_w, vo_h = int(m.group(1)), int(m.group(2))
                if self._window:
                    self._window.resize(self._vo_size)
                if "aspect" not in self._file_info or self._file_info["aspect"] == 0:
                    # No aspect defined, so base it on vo size.
                    self._file_info["aspect"] = vo_w / float(vo_h)

        elif line.startswith("overlay:") and line.find("reusing") == -1:
            m = re.search("(\d+)x(\d+)", line)
            if m:
                width, height = int(m.group(1)), int(m.group(2))
                if self._overlay_shmem:
                    self._overlay_shmem.detach()
                self._overlay_shmem = shm.memory(shm.getshmid(self._get_overlay_shm_key()))
                self._overlay_shmem.attach()

                self.signals["osd_configure"].emit(width, height, self._overlay_shmem.addr + 16,
                                                   width, height)


        elif line.startswith("Parsing input"):
            # Delete the temporary key input file.
            file = line[line.find("file")+5:]
            os.unlink(file)

        elif line.startswith("File not found"):
            file = line[line.find(":")+2:]
            raise IOError, (2, "No such file or directory: %s" % file)

        elif line.startswith("FATAL:"):
            raise MPlayerError, line.strip()

        if self._debug:
            if re.search("@@@|outbuf|overlay", line, re.I) and self._debug == 1:
                print line
            elif line[:2] not in ("A:", "V:") and self._debug == 2:
                print line
            elif self._debug == 3:
                print line

        if line.strip():
            self.signals["output"].emit(line)
            self._last_line = line


    def _get_overlay_shm_key(self):
        name = "mplayer-overlay.%s" % self._instance_id
        return int(md5.md5(name).hexdigest()[:7], 16)


    def _start(self, file, user_args = ""):
        assert(self._mp_info)

        keyfile = self._make_dummy_input_config()

        filters = self._filters_pre[:]
        if self._size:
            w, h = self._size
            filters += ["scale=%d:-2" % w, "expand=%d:%d" % (w, h), "dsize=%d:%d" % (w,h) ]

        args = "-v -slave -osdlevel 0 -nolirc -nojoystick -nomouseinput " \
               "-nodouble -fixed-vo -identify -framedrop "

        #filters += ["outbuf=4342321:1"]
        filters += self._filters_add
        filters += ["expand=:::::4/3"]
        filters += ["overlay=%s" % self._get_overlay_shm_key()]

        if filters:
            args += "-vf %s " % string.join(filters, ",")

        if self._window:
            args += "-wid %s " % hex(self._window.get_id())
            args += "-display %s " % self._window.get_display().get_string()
            args += "-input conf=%s " % keyfile

        args += "%s " % user_args
        if file:
            args += "\"%s\"" % file

        self._spawn(args)
        self._state = STATE_OPENING


    def _slave_cmd(self, cmd):
        if not self.is_alive():
            return False

        if self._debug >= 1:
            print "SLAVE:", cmd
        self._process.write(cmd + "\n")


    def _exited(self, exitcode):
        self._state = STATE_NOT_RUNNING
        kaa.signals["shutdown"].disconnect(self.stop)
        self.signals["end"].emit()
        if exitcode != 0:
            raise MPlayerExitError, (exitcode, self._last_line)


    def is_alive(self):
        return self._process and self._process.is_alive()

    def open(self, mrl):
        # FIXME: parse mrl form
        self._mrl = mrl
        if self._window == None:
            # Use the user specified size, or some sensible default.
            win_size = self._size or (640, 480)
            self._window = display.X11Window(size = win_size, title = "MPlayer Window")


    def play(self):
        if self.get_state() == STATE_PAUSED:
            self._slave_cmd("pause")
        elif self.get_state() == STATE_NOT_RUNNING:
            file = self._mrl
            user_args = ""

            if not self._mp_info:
                # We're probably waiting for _get_mplayer_info() to finish; set
                # state so that _handle_mp_info() will call _start().  There's no
                # race condition here if we're currently in the main thread,
                # because _handle_mp_info() is guaranteed to be called in the
                # main thread.
                self._state = STATE_OPENING
                self._state_data = (file, user_args) 
                return False

            self._start(file, user_args)
            return True

    def pause(self):
        if self.get_state() == STATE_PLAYING:
            self._slave_cmd("pause")
            self._eat_ticks += 1

    def pause_toggle(self):
        if self.get_state() == STATE_PAUSED:
            self.play()
        else:       
            self.pause()


    def seek_relative(self, offset):
        self._slave_cmd("seek %f 0" % offset)

    def seek_absolute(self, position):
        self._slave_cmd("seek %f 2" % position)

    def seek_percentage(self, percent):
        self._slave_cmd("seek %f 1" % percent)


    def stop(self):
        # TODO: maybe look at -idle
        self._slave_cmd("quit")
        # Could be paused, try sending again.
        self._slave_cmd("quit")


    def get_vo_size(self):
        return self._vo_size

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
                cmd.append("invalidate=%d:%d:%d:%d" % (x, y-1, w, h+1))
        self._slave_cmd("overlay %s" % ",".join(cmd))
        self._overlay_set_lock(MPlayer.OVERLAY_BUFFER_LOCKED)


    def osd_can_update(self, byte):
        try:
            if ord(self._overlay_shmem.read(1)) == MPlayerOSDCanvas.BUFFER_UNLOCKED:
                return True
        except:
            self._overlay_shmem = None

        return False


    def _overlay_set_lock(self, byte):
        if self._overlay_shmem and self._overlay_shmem.attached:
            self._overlay_shmem.write(chr(byte))


    def get_player_id(self):
        return "mplayer"


def get_capabilities():
    capabilities = CAP_VIDEO | CAP_AUDIO | CAP_VARIABLE_SPEED
    # FIXME: we don't know if these caps exist until _get_mplayer_info()
    # returns.
    capabilities |= CAP_OSD | CAP_CANVAS
    schemes = ["file", "vcd", "cdda", "cue", "tivo", "http", "mms", "rtp",
                "rtsp", "ftp", "udp", "sdp"]
    return capabilities, schemes

register_player("mplayer", MPlayer, get_capabilities)
