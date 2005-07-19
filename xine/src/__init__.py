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

    if type(obj) == _xine.VideoPort:
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

    obj.wrapper = weakref.ref(o)
    return o


class Xine(object):
    def __init__(self):
        self._xine = _xine.Xine()
        self._xine.log_callback = notifier.WeakCallback(self._log_callback)
        self.signals = {
            "log": notifier.Signal()
        }

    def _default_frame_output_cb(self, width, height, aspect, window):
        #print "FRAME CALLBACK", width, height, aspect, window.get_geometry()
        if window:
            win_w, win_h = window.get_geometry()[1]
        else:
            win_w, win_h = 640, 480
        # Return order: dst_pos, win_pos, dst_size, aspect
        aspect = width / height
        w = win_w
        h = w / aspect
        y = (win_h-h)/2
        return (0, y), (0, 0), (w, h), 1

    def open_video_driver(self, driver = "auto", **kwargs):
        if "window" in kwargs:
            window = kwargs["window"]
            assert(type(window) == display.X11Window)
            if "frame_output_cb" not in kwargs:
                kwargs["frame_output_cb"] = notifier.WeakCallback(self._default_frame_output_cb, window)
            if "dest_size_cb" not in kwargs:
                kwargs["dest_size_cb"] = self._default_frame_output_cb
            kwargs["window"] = window._window
            self._xine.dependencies.append(window._window)

        
        vo = self._xine.open_video_driver(driver, **kwargs)
        return _wrap_xine_object(vo)


    def open_audio_driver(self, driver = "auto", **kwargs):
        ao = self._xine.open_audio_driver(driver, **kwargs)
        return _wrap_xine_object(ao)


    def stream_new(self, audio_port, video_port):
        assert(type(audio_port) == AudioPort)
        assert(type(video_port) == VideoPort)

        stream = self._xine.stream_new(audio_port._ao, video_port._vo)
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
            ao.append(item._ao)
        vo = []
        for item in video_targets:
            assert(type(item) == VideoPort)
            vo.append(item._vo)

        post = self._xine.post_init(name, inputs, ao, vo)
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
        print "LOG", section
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
        self._vo = vo

    def get_post_plugin(self):
        return _wrap_xine_object(self._vo.post)


class AudioPort(object):
    def __init__(self, ao):
        self._ao = ao

    def get_post_plugin(self):
        return _wrap_xine_object(self._ao.post)

class Stream(object):
    def __init__(self, stream):
        self._stream = stream

    def open(self, mrl):
        return self._stream.open(mrl)

    def play(self, pos = 0, time = 0.0):
        return self._stream.play(pos, int(time*1000))

    def get_video_source(self):
        return _wrap_xine_object(self._stream.get_source("video"))

    def get_audio_source(self):
        return _wrap_xine_object(self._stream.get_source("audio"))

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
        return self._stream.get_pos_length()

    def get_info(self, info):
        return self._stream.get_info(info)

    def get_meta_info(self, info):
        return self._stream.get_meta_info(info)

class Post(object):
    def __init__(self, post):
        self._post = post

    def get_video_inputs(self):
        l = []
        for item in self._post.get_video_inputs():
            l.append(_wrap_xine_object(item))
        return l

    def get_audio_inputs(self):
        l = []
        for item in self._post.get_audio_inputs():
            l.append(_wrap_xine_object(item))
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

    def get_identifier(self):
        return self._post.get_identifier()

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

#    def wire(self, input):
#        output = self.get_output


class PostOut(object):
    def __init__(self, post_out):
        self._post_out = post_out

    def wire(self, input):
        if type(input) == PostIn:
            return self._post_out.wire(input._post_in)
        elif type(input) == VideoPort:
            return self._post_out.wire_video_port(input._vo)
        elif type(input) == AudioPort:
            return self._post_out.wire_audio_port(input._ao)
        else:
            raise XineError, "Unsupported input type: " + str(type(input))

    def get_post_plugin(self):
        if type(self._post_out.post) == _xine.Post:
            return _wrap_xine_object(self._post_out.post)

    def get_stream(self):
        if type(self._post_out.post) == _xine.Stream:
            return _wrap_xine_object(self._post_out.post)

    def get_output_type(self):
        if type(self._post_out.post) == _xine.Stream:
            return Stream
        elif type(self._post_out.post) == _xine.Post:
            return Post
        
    def get_output(self):
        if self.get_output_type() == Stream:
            return self.get_stream()
        return self.get_post_plugin()


class PostIn(object):
    def __init__(self, post_in):
        self._post_in = post_in

    def get_post_plugin(self):
        return _wrap_xine_object(self._post_in.post)
