import weakref
import _xine
from kaa import display, notifier
from kaa.base.version import Version
from constants import *

XineError = _xine.XineError

def get_version():
    return Version(_xine.get_version())

def _wrap_xine_object(obj):
    if obj == None:
        return obj

    if obj.wrapper and obj.wrapper():
        return obj.wrapper()

    if type(obj) == _xine.Xine:
        o = Xine(obj)
    elif type(obj) == _xine.VideoPort:
        o = VideoPort(obj)
    elif type(obj) == _xine.AudioPort:
        o = AudioPort(obj)
    elif type(obj) == _xine.Stream:
        o = Stream(obj)
    elif type(obj) == _xine.Post:
        o = Post(obj)
    elif type(obj) == _xine.PostOut:
        o = PostOut(obj)
    elif type(obj) == _xine.PostIn:
        o = PostIn(obj)
    else:
        raise TypeError, "Unknown xine object: " + str(obj)

    obj.wrapper = weakref.ref(o)
    return o



def _debug_show_chain(o, level = 0):
    # For debugging, shows the post chain
    indent = " " * level
    if type(o) == _xine.Stream:
        print "%s [STREAM] %s " % (indent, repr(o)), o
        print "%s   Video:" % indent
        vt = o.video_source.wire_object
        _debug_show_chain(vt, level + 5)
        print "%s   Audio:" % indent
        at = o.audio_source.wire_object
        _debug_show_chain(at, level + 5)
    elif type(o) == _xine.PostIn:
        post = o.owner
        print '%s  -> [POST IN %s / %s]' % (indent, post.name, o.get_name()), o
        for output in post.list_outputs():
            _debug_show_chain(post.post_output(output), level)
    elif type(o) == _xine.PostOut:
        if type(o.owner) == _xine.Stream:
            target = o.wire_object
            name = "(stream)"
        else:
            if type(o.port.wire_object) == list:
                target = o.port
            else:
                target = o.port.wire_object
            name = o.owner.name
        print '%s  -> [POST OUT %s / %s]' % (indent, name, o.get_name()), o
        _debug_show_chain(target, level + 5)
    elif type(o) == _xine.VideoPort:
        print '%s  -> [VIDEO DRIVER]' % indent, o
    elif type(o) == _xine.AudioPort:
        print '%s  -> [AUDIO DRIVER]' % indent, o
    elif o == None:
        print '%s  -> [NONE]' % indent
    else:
        print '%s  -> [UNKNOWN]' % indent, o



class Xine(object):
    def __init__(self, xine = None):
        if xine:
            self._xine = xine
            return

        self._xine = _xine.Xine()
        self._xine.log_callback = notifier.WeakCallback(self._log_callback)
        self.signals = {
            "log": notifier.Signal()
        }
        self._xine.wrapper = weakref.ref(self)

    def _default_frame_output_cb(self, width, height, aspect, window):
        #print "FRAME CALLBACK", width, height, aspect, window
        if window:
            win_w, win_h = window.get_geometry()[1]
        else:
            win_w, win_h = 640, 480
        # Return order: dst_pos, win_pos, dst_size, aspect
        movie_aspect = width / float(height)
        w = win_w
        h = int(w / movie_aspect)
        y = int((win_h-h)/2)
        return (0, 0), (0, 0), (win_w, win_h), 1

    def _default_dest_size_cb(self, width, height, aspect, window):
        if window:
            win_w, win_h = window.get_geometry()[1]
        else:
            win_w, win_h = 640, 480
        return (win_w, win_h), 1

    def open_video_driver(self, driver = "auto", **kwargs):
        if "window" in kwargs:
            window = kwargs["window"]
            assert(type(window) == display.X11Window)
            if "frame_output_cb" not in kwargs:
                kwargs["frame_output_cb"] = notifier.WeakCallback(self._default_frame_output_cb, window)
            if "dest_size_cb" not in kwargs:
                kwargs["dest_size_cb"] = notifier.WeakCallback(self._default_dest_size_cb, window)
            kwargs["window"] = window._window
            self._xine.dependencies.append(window._window)

        
        vo = self._xine.open_video_driver(driver, **kwargs)
        # This port is a driver, initialize wire_object to empty list.
        vo.wire_object = []
        return _wrap_xine_object(vo)
                    


    def open_audio_driver(self, driver = "auto", **kwargs):
        ao = self._xine.open_audio_driver(driver, **kwargs)
        # This port is a driver, initialize wire_object to empty list.
        ao.wire_object = []
        return _wrap_xine_object(ao)


    def stream_new(self, audio_port, video_port):
        assert(type(audio_port) == AudioPort)
        assert(type(video_port) == VideoPort)

        stream = self._xine.stream_new(audio_port._port, video_port._port)
        # Set wire_objects for stream outputs
        vsource = stream.video_source
        asource = stream.audio_source
        vsource.wire_object = video_port._port
        if vsource not in video_port._port.wire_object:
            video_port._port.wire_object.append(vsource)

        asource.wire_object = audio_port._port
        if asource not in audio_port._port.wire_object:
            audio_port._port.wire_object.append(asource)

        for dep in self._xine.dependencies:
            if type(dep) == display._Display.X11Window:
                video_port._port.send_gui_data(GUI_SEND_DRAWABLE_CHANGED, dep.ptr)
                video_port._port.send_gui_data(GUI_SEND_VIDEOWIN_VISIBLE, 1)

        return _wrap_xine_object(stream)

    def list_video_plugins(self):
        return self._xine.list_plugins("video")

    def list_audio_plugins(self):
        return self._xine.list_plugins("audio")

    def list_post_plugins(self, types = -1):
        return self._xine.list_plugins("post", types)

    def list_demuxer_plugins(self):
        return self._xine.list_plugins("demuxer")

    def list_input_plugins(self):
        return self._xine.list_plugins("input")

    def list_spu_plugins(self):
        return self._xine.list_plugins("spu")

    def list_audio_decoder_plugins(self):
        return self._xine.list_plugins("audio_decoder")

    def list_video_decoder_plugins(self):
        return self._xine.list_plugins("video_decoder")

    def post_init(self, name, inputs = 0, audio_targets = [], video_targets = []):
        assert(type(audio_targets) in (list, tuple))
        assert(type(video_targets) in (list, tuple))
        ao = []
        for item in audio_targets:
            assert(type(item) == AudioPort)
            ao.append(item._port)
        vo = []
        for item in video_targets:
            assert(type(item) == VideoPort)
            vo.append(item._port)

        post = self._xine.post_init(name, inputs, ao, vo)

        # Post outputs are wired to a/v ports.
        for output in post.outputs:
            if output.get_type() in (POST_DATA_VIDEO, POST_DATA_AUDIO):
                if output.port not in output.port.wire_object:
                    output.port.wire_object.append(output)

        # Post inputs are unconnected; initialize them to a empty list.
        for input in post.inputs:
            if input.get_type() in (POST_DATA_VIDEO, POST_DATA_AUDIO):
                input.port.wire_object = []

        return _wrap_xine_object(post)

    def get_log_names(self):
        return self._xine.get_log_names()

    def _resolve_log_section_name(self, section):
        return section

    def get_log(self, section):
        if type(section) == str:
            sections = self.get_log_names()
            if section not in sections:
                raise XineError, "Unknown log section: " + section
            section = sections.index(section)
        return self._xine.get_log(section)


    def _log_callback(self, section):
        sections = self.get_log_names()
        section = sections[section]
        self.signals["log"].emit(section)
 
    def get_parameter(self, param):
        return self._xine.get_engine_param(param)

    def set_parameter(self, param, value):
        return self._xine.set_engine_param(param, value)
      
    def get_browsable_input_plugin_ids(self):
        return self._xine.get_input_plugin_ids("browsable")

    def get_browse_mrls(self, plugin, start_mrl = None):
        return self._xine.get_browse_mrls(plugin, start_mrl)

    def get_autoplay_input_plugin_ids(self):
        return self._xine.get_input_plugin_ids("autoplay")

    def get_autoplay_mrls(self, plugin):
        return self._xine.get_autoplay_mrls(plugin)

    def get_file_extensions(self):
        return self._xine.get_file_extensions().split(" ")

    def get_mime_types(self):
        types = []
        for t in self._xine.get_mime_types().split(";"):
            vals = map(lambda x: x.strip(), t.split(":"))
            if len(vals) > 1:
                vals[1] = tuple(vals[1].split(","))
            types.append(tuple(vals))
        return types

class VideoPort(object):
    def __init__(self, vo):
        self._port = vo

    def get_owner(self):
        # Can be Xine, Post, or Stream object
        return _wrap_xine_object(self._port.owner)


class AudioPort(object):
    def __init__(self, ao):
        self._port = ao

    def get_owner(self):
        # Can be Xine, Post, or Stream object
        return _wrap_xine_object(self._port.owner)


class Stream(object):
    def __init__(self, stream):
        self._stream = stream

    def open(self, mrl):
        return self._stream.open(mrl)

    def play(self, time = 0.0, pos = 0):
        return self._stream.play(pos, int(time*1000))

    def get_video_source(self):
        return _wrap_xine_object(self._stream.video_source)

    def get_audio_source(self):
        return _wrap_xine_object(self._stream.audio_source)

    def slave(self, slave, affection = 0xff):
        assert(type(slave) == Stream)
        assert(slave != self)
        return self._stream.slave(slave._stream, affection)

    def set_trick_mode(self, mode, value):
        return self._stream.set_trick_mode(mode, value)

    def stop(self):
        return self._stream.stop()

    def close(self):
        return self._stream.close()

    def eject(self):
        return self._stream.eject()

    def get_current_vpts(self):
        return self._stream.get_current_vpts()

    def get_status(self):
        return self._stream.get_status()

    def get_error(self):
        return self._stream.get_error()

    def get_audio_lang(self, channel = -1):
        return self._stream.get_lang("audio", channel)

    def get_spu_lang(self, channel = -1):
        return self._stream.get_lang("spu", channel)

    def get_pos_length(self):
        stream, time, length = self._stream.get_pos_length()
        time /= 1000.0
        return stream, time, length

    def get_stream_pos(self):
        return self.get_pos_length()[0]

    def get_time(self):
        return self.get_pos_length()[1]

    def get_length(self):
        return self.get_pos_length()[2]

    def get_info(self, info):
        return self._stream.get_info(info)

    def get_meta_info(self, info):
        return self._stream.get_meta_info(info)

    def get_parameter(self, param):
        return self._stream.get_param(param)

    def set_parameter(self, param, value):
        return self._stream.set_param(param, value)

    def _seek(self, time):
        if self.get_status() != STATUS_PLAY:
            print "Stream not playing"
            return False
        speed = self.get_parameter(PARAM_SPEED)
        self.set_parameter(PARAM_SPEED, SPEED_NORMAL)
        if not self.get_parameter(STREAM_INFO_SEEKABLE):
            print "Stream not seekable"
            return False

        self.play(time)
        self.set_parameter(PARAM_SPEED, speed)
        
    def seek_relative(self, offset):
        t = max(0, self.get_time() + offset)
        print t
        return self._seek(t)

    def seek_absolute(self, t):
        t = max(0, time)
        return self._seek(t)



class Post(object):
    def __init__(self, post):
        self._post = post

    def get_video_inputs(self):
        l = []
        for input in self._post.inputs:
            if input.get_type() == POST_DATA_VIDEO:
                l.append(_wrap_xine_object(input.port))
        return l

    def get_audio_inputs(self):
        l = []
        for input in self._post.inputs:
            if input.get_type() == POST_DATA_AUDIO:
                l.append(_wrap_xine_object(input.port))
        return l

    def get_parameters_desc(self):
        return self._post.get_parameters_desc()

    def get_parameters(self):
        return self._post.get_parameters()

    def set_parameters(self, **kwargs):
        parms = self.get_parameters_desc()
        for key, value in kwargs.items():
            assert(key in parms)
            assert(type(value) == parms[key]["type"])

        return self._post.set_parameters(kwargs)

    def get_name(self):
        return self._post.name

    def get_description(self):
        return self._post.get_description()

    def get_help(self):
        return self._post.get_help()

    def list_inputs(self):
        return self._post.list_inputs()

    def list_outputs(self):
        return self._post.list_outputs()

    def get_output(self, name):
        return _wrap_xine_object(self._post.post_output(name))

    def get_input(self, name):
        return _wrap_xine_object(self._post.post_input(name))

    def unwire(self):
        for name in self.list_outputs():
            output = self.get_output(name)
            output.unwire()


class PostOut(object):
    def __init__(self, post_out):
        self._post_out = post_out

    def wire(self, input):
        if type(input) == PostIn:
            if self._post_out.wire_object == input._post_in:
                return
            r = self._post_out.wire(input._post_in)
            if r:
                self._rewire(input._post_in)
            return r

        elif type(input) == VideoPort:
            if self._post_out.wire_object == input._port:
                return
            r = self._post_out.wire_video_port(input._port)
            if r:
                self._rewire(input._port)
            return r

        elif type(input) == AudioPort:
            if self._post_out.wire_object == input._port:
                return
            r = self._post_out.wire_audio_port(input._port)
            if r:
                self._rewire(input._port)
            return r
        else:
            raise XineError, "Unsupported input type: " + str(type(input))

    def _rewire(self, target):
        self._unwire()
        if type(self.get_owner()) == Stream:
            # Special case for streams
            self._post_out.wire_object = target
        else:
            self.get_port()._port.wire_object = target

        if type(target) in (_xine.PostIn, _xine.PostOut):
            target_port = target.port
        elif type(target) in (_xine.VideoPort, _xine.AudioPort):
            target_port = target
        else:
            raise XineError, "Unsupported wire target: " + str(type(target))

        self._post_out.wire_object = target

        if self._post_out not in target_port.wire_object:
            target_port.wire_object.append(self._post_out)

    def _unwire(self):
        if not self._post_out.wire_object:
            return

        # Target is either a PostIn or a Port.
        target = self._post_out.wire_object
        if type(target) == _xine.PostIn:
            # It's a PostIn, so get the wire object list via its Port.
            target_sources = target.port.wire_object
        else:
            # Must be a Video/Audio Port.
            target_sources = target.wire_object
        if self._post_out not in target_sources:
            raise XineError, "Consistency error in _unwire()"
        target_sources.remove(self._post_out)
        self._post_out.wire_object = None

    def unwire(self):
        if type(self.get_owner()) == Stream:
            # XXX: we could do this automatically ...
            raise XineError, "Can't unwire a Stream source.  Try rewiring to a null port."

        # Given previous -> me -> next, connect previous to next.  The problem
        # is that for multiple inputs/outputs this could do the wrong thing.
        # So we make a guess and use the first input/output and hope for the
        # best.  If anything more intelligent is needed, it will have to be
        # done manually.
        port = self._post_out.port
        if type(port.wire_object) == list: 
            # We're wired to a video device.
            old_target = _wrap_xine_object(port)
        else:
            old_target = _wrap_xine_object(port.wire_object)
        self._unwire()

        # If we're here, owner is a Post.
        post = self._post_out.owner
        # Get the default input for the Post object.
        input = post.post_input(post.list_inputs()[0])
        # Get each PostOut connected to this.
        for previous in input.port.wire_object:
            # Wire this one to our old target.
            _wrap_xine_object(previous).wire(old_target)


        
    def get_type(self):
        # POST_DATA_VIDEO or POST_DATA_AUDIO
        return self._post_out.get_type()

    def get_name(self):
        return self._post_out.get_name()

    def get_owner(self):
        # Can be Post or Stream
        return _wrap_xine_object(self._post_out.owner)

    def get_port(self):
        return _wrap_xine_object(self._post_out.port)


class PostIn(object):
    def __init__(self, post_in):
        self._post_in = post_in

    def get_owner(self):
        # Post object
        return _wrap_xine_object(self._post_in.owner)

    def get_type(self):
        # POST_DATA_VIDEO or POST_DATA_AUDIO
        return self._post_in.get_type()

    def get_name(self):
        return self._post_in.get_name()

    def get_port(self):
        return _wrap_xine_object(self._post_in.port)
