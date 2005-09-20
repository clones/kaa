import os, re, string, tempfile, time, stat

from kaa import notifier, display
import kaa

# 0 = none, 1 = interesting lines, 2 = everything, 3 = everything + status
DEBUG=0

# A cache holding values specific to an MPlayer executable (version,
# filter list, video/audio driver list, input keylist).  This dict is
# keyed on the full path of the MPlayer binary.
_cache = {}

def _get_mplayer_info(path, mtime = None):
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
        signal = notifier.Signal()
        thread = notifier.Thread(_get_mplayer_info, path, mtime)
        # Thread class ensures the callbacks get invoked in the main thread.
        thread.signals["completed"].connect(signal.emit)
        thread.signals["exception"].connect(signal.emit)
        thread.start()
        return signal

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

class MPlayer(object):

    PATH = None
    _instance_count = 0


    RE_STATUS = re.compile("V:\s*([\d+\.]+)|A:\s*([\d+\.]+)\s\W")

    def __init__(self, size = None, window = None):
        self._mp_cmd = MPlayer.PATH
        if not self._mp_cmd:
            for dir in os.getenv("PATH").split(":"):
                cmd = os.path.join(dir, "mplayer")
                if os.path.exists(cmd):
                    self._mp_cmd = cmd
                    break

        if not self._mp_cmd:
            raise MPlayerError, "No MPlayer executable found in PATH"

        # Caller can pass his own X11Window here.  If it's None, it will
        # get created in the play() call.  If it's False, no X11Window will
        # be created and MPlayer will create its own window.
        assert(window in (None, False) or type(window) == display.X11Window)
        self._window = window
        # Requested size of the video window (will be soft scaled/expanded)
        self._size = size

        # Used for vf_osd and vf_outbuf
        self._instance_id = "%d-%d" % (os.getpid(), MPlayer._instance_count)
        MPlayer._instance_count += 1

        # Size of the window as reported by MPlayer (aspect-corrected)
        self._vo_size = None 
        self._process = None
        self._state = "exited"
        self._state_data = None

        self._file_info = {}
        self._position = 0.0
        self._eat_ticks = 0
        self._filters_pre = []
        self._filters_add = []
        self._last_line = None
        
        self.signals = {
            "output": notifier.Signal(),
            "quit": notifier.Signal(),
            "pause": notifier.Signal(),
            "play": notifier.Signal(),
            "pause_toggle": notifier.Signal(),
            "seek": notifier.Signal(),
            "tick": notifier.Signal(),
            "start": notifier.Signal()
        }

        self._mp_info = _get_mplayer_info(self._mp_cmd)
        if type(self._mp_info) == notifier.Signal:
            self._mp_info.connect(self._handle_mp_info)
            self._mp_info = None


    def _spawn(self, args, hook_notifier = True):
        self._process = notifier.Process(self._mp_cmd)
        self._process.start(args)
        if hook_notifier:
            self._process.signals["stdout"].connect(self._handle_line)
            self._process.signals["stderr"].connect(self._handle_line)
            self._process.signals["completed"].connect(self._exited)
            self._process.set_stop_command(self.quit)
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
            # TODO: handle me
            raise info
        self._mp_info = info
        if self._state == "pending":
            file, user_args = self._state_data
            self._state_data = None
            self._play(file, user_args)


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
                else:
                    self.signals["tick"].emit(self._position)

                # XXX this logic won't work with seek-while-paused patch; state
                # will be "playing" after a seek.
                if self._state == "paused":
                    self.signals["pause_toggle"].emit()
                if self._state not in ("paused", "playing"):
                    self._state = "playing"
                    self.signals["start"].emit()
                elif self._state != "playing":
                    self._state = "playing"
                    self.signals["play"].emit()

        elif line.startswith("ID_") and line.find("=") != -1:
            attr, value = line.split("=")
            attr = attr[3:]
            info = { "VIDEO_FORMAT": ("vformat", str),
                     "VIDEO_BITRATE": ("vbitrate", int),
                     "VIDEO_WIDTH": ("width", int),
                     "VIDEO_HEIGHT": ("height", int),
                     "VIDEO_FPS": ("fps", float),
                     "VIDEO_ASPECT": ("aspect", float),
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

        elif line.startswith("  =====  PAUSE"):
            self._state = "paused"
            self.signals["pause_toggle"].emit()
            self.signals["pause"].emit()
            

        elif line.startswith("Parsing input"):
            # Delete the temporary key input file.
            file = line[line.find("file")+5:]
            os.unlink(file)

        elif line.startswith("File not found"):
            file = line[line.find(":")+2:]
            raise IOError, (2, "No such file or directory: %s" % file)

        elif line.startswith("FATAL:"):
            raise MPlayerError, line.strip()

        if DEBUG:
            if re.search("@@@|outbuf|osd", line, re.I) and DEBUG == 1:
                print line
            elif line[:2] not in ("A:", "V:") and DEBUG == 2:
                print line
            elif DEBUG == 3:
                print line

        if line.strip():
            self.signals["output"].emit(line)
            self._last_line = line


    def _play(self, file, user_args = ""):
        assert(self._mp_info)

        keyfile = self._make_dummy_input_config()

        filters = self._filters_pre[:]
        if self._size:
            w, h = self._size
            filters += ["scale=%d:-2" % w, "expand=%d:%d" % (w, h), "dsize=%d:%d" % (w,h) ]

        args = "-v -slave -osdlevel 0 -nolirc -nojoystick -nomouseinput " \
               "-nodouble -fixed-vo -identify -framedrop "

        filters += self._filters_add

        if filters:
            args += "-vf %s " % string.join(filters, ",")

        if self._window:
            args += "-wid %s " % self._window.get_id()
            args += "-display %s " % self._window.get_display().get_string()
            args += "-input conf=%s " % keyfile

        args += "%s " % user_args
        if file:
            args += "\"%s\"" % file

        self._spawn(args)
        self._state = "loading"


    def _slave_cmd(self, cmd):
        if DEBUG >= 1:
            print "SLAVE:", cmd
        self._process.write(cmd + "\n")


    def _exited(self, exitcode):
        self._state = "exited"
        kaa.signals["shutdown"].disconnect(self.quit)
        self.signals["quit"].emit()
        if exitcode != 0:
            raise MPlayerExitError, (exitcode, self._last_line)


    def is_alive(self):
        return self._process and self._process.is_alive()


    def play(self, file, user_args = ""):
        if self._window == None:
            # Use the user specified size, or some sensible default.
            win_size = self._size or (640, 480)
            self._window = display.X11Window(size = win_size, title = "MPlayer Window")

        if not self._mp_info:
            # We're probably waiting for _get_mplayer_info() to finish; set
            # state so that _handle_mp_info() will call _play().  There's no
            # race condition here if we're currently in the main thread,
            # because _handle_mp_info() is guaranteed to be called in the
            # main thread.
            self._state = "pending"
            self._state_data = (file, user_args) 
            return False

        self._play(file, user_args)
        return True

    def is_paused(self):
        return self.get_state() == "paused"


    def get_state(self):
        return self._state


    def set_state(self, state):
        if state == self._state or not self.is_alive():
            return False

        if state == "paused" and self.get_state() == "playing":
            self._slave_cmd("pause")
            self._eat_ticks += 1
        elif state == "playing" and self.get_state() == "paused":
            self._slave_cmd("pause")

        return True
 
 
    def pause(self):
        if self.get_state() == "paused":
            self.set_state("playing")
        else:       
            self.set_state("paused")


    def seek(self, offset, rel = 0):
        if not self.is_alive():
            return False

        self._slave_cmd("seek %f %d" % (offset, rel))


    def quit(self):
        if not self.is_alive():
            return False

        self._slave_cmd("quit")
        # Could be paused, try sending again.
        self._slave_cmd("quit")


    def get_window(self):
        return self._window


    def get_vo_size(self):
        return self._vo_size

    def get_position(self):
        return self._position

    def get_file_info(self):
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

    def get_instance_id(self):
        return self._instance_id
