import weakref
import _xine
from kaa import display, notifier

XineError = _xine.XineError

def _wrap_xine_object(obj):
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

    def list_post_plugins(self):
        return self._xine.list_plugins("post")


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


class VideoPort(object):
    def __init__(self, vo):
        self._vo = vo


class AudioPort(object):
    def __init__(self, ao):
        self._ao = ao


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


class PostIn(object):
    def __init__(self, post_in):
        self._post_in = post_in
