import _xine
from kaa import display

class Xine(object):
    def __init__(self):
        self._xine = _xine.Xine()

    def open_video_driver(self, driver = "auto", **kwargs):
        if "window" in kwargs:
            assert(type(kwargs["window"]) == display.X11Window)
            kwargs["window"] = kwargs["window"]._window
            self._xine.dependencies.append(kwargs["window"])
        
        vo = self._xine.open_video_driver(driver, **kwargs)
        return VideoPort(vo)


    def open_audio_driver(self, driver = "auto", **kwargs):
        ao = self._xine.open_audio_driver(driver, **kwargs)
        return AudioPort(ao)


    def stream_new(self, audio_port, video_port):
        assert(type(audio_port) == AudioPort)
        assert(type(video_port) == VideoPort)

        stream = self._xine.stream_new(audio_port._ao, video_port._vo)
        return Stream(stream)


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

