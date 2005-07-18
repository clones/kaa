import weakref
import _xine
from kaa import display

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

    obj.wrapper = weakref.ref(o)
    return o


class Xine(object):
    def __init__(self):
        self._xine = _xine.Xine()

    def open_video_driver(self, driver = "auto", **kwargs):
        if "window" in kwargs:
            assert(type(kwargs["window"]) == display.X11Window)
            kwargs["window"] = kwargs["window"]._window
            self._xine.dependencies.append(kwargs["window"])
        
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

    def play(self, pos = 0, time = 0):
        return self._stream.play(pos, time)


class Post(object):
    def __init__(self, post):
        self._post = post

    def get_video_inputs(self):
        l = []
        for item in self._post.get_video_inputs():
            l.append(_wrap_xine_object(item))
        return l

    def get_parameters_desc(self):
        return self._post.get_parameters_desc()

    def get_parameters(self):
        return self._post.get_parameters()

    def set_parameters(self, values):
        assert(type(values) == dict)
        parms = self.get_parameters_desc()
        for key, value in values.items():
            assert(key in parms)
            assert(type(value) == parms[key]["type"])

        return self._post.set_parameters(values)

    def set_parameter(self, param, value):
        return self.set_parameters({param: value})
