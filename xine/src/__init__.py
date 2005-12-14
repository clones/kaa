import weakref, threading, math, os

import _xine
import kaa
from kaa import display, notifier, metadata
from kaa.base.version import Version
from constants import *

# FIXME: find a good place to document this:
#
# POST MAGIC:
#
#  - Post has an arbitrary number of inputs (PostIn) and outputs (PostOut).
#  - PostOuts are wired to Audio/Video Ports.  The Port can be either
#    a audio/video device, or a port belonging to a PostIn object.
#  - PostIns act as Audio/Video ports:
#         postout.wire(postin) == postout.wire(postin.get_port())
#  - PostOuts are always wired to something (i.e. PostOut.get_port() is
#    never None).  By default they are wired to the audio/video targets
#    listed when the post is created.
#  - Whether or not a Post is actually "in the chain" depends on if there
#    exists a PostOut that's wired to one of its PostIn inputs which is
#    ultimately being fed by a Stream.
#  - Streams have two PostOut objects, a video source and an audio source.
#    The ports of these PostOuts is a Xine object.  These sources are by
#    default wired to the audio/video targets when the stream is created.
#
#
# Internal view (i.e. types from the _xine module):
#
#     Post.inputs: list of PostIn
#     Post.outputs: list of PostOut
#
#     PostIn.owner: The Post object the input belongs to
#     PostIn.get_port(): VideoPort or AudioPort for that PostIn. (STATIC)
#
#     PostOut.owner: The Post or Stream object the output belongs to
#     PostOut.get_port(): VideoPort or AudioPort this PostOut is wired to.
#                        (CHANGES based on what it's wired to.)
#
#     VideoPort.owner: Owner of the port: if owner is a Xine object,
#                      the port is a DEVICE; if owner is a PostIn object
#                      then the port is an input of a Post object.
#     VideoPort.wire_list: A list of PostOut objects that is wired to this 
#                          VideoPort.
# 
#         - and same above for AudioPort
#
# Reference chain looks like this:
#
#                              
#                   -> Post Out (Audio source) --> (same as video source)
#                  / 
#    Xine <- Stream 
#                  \
#                   > Post Out (Video source)
#                        |
#                        +-> Video <==> Post In
#                            Port         ||
#                                         +> Post -> Post Out
#                                                     |
#                                                     -> Video Port [<==> ...]
#
# Where:
#    A -> B    means  A holds a reference to B (and therefore B will not be
#                     dealloc'd before A)
#    A <==> B  means  A holds a ref to B, and B holds a ref to A (cycle),
#                     so GC support is needed in both A and B.  Dealloc order
#                     non-deterministic.
#
# All objects also hold a reference to Xine object (not diagrammed for 
# simplicity).
#
# Objects should dealloc starting with Stream.  (Audio|Video)Port, PostIn 
# and Post need gc support.
# 

XineError = _xine.XineError

# Constants for special kaa vo
GUI_SEND_KAA_VO_GET_CONTROL     = 1000


def get_version():
    return Version(_xine.get_version())

def _wrap_xine_object(obj):
    if obj == None:
        return obj

    if obj.wrapper and obj.wrapper():
        return obj.wrapper()

    if type(obj) == _xine.Xine:
        o = Xine(obj)
    elif type(obj) == _xine.VODriver:
        o = VODriver(obj)
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
    elif type(obj) == _xine.EventQueue:
        o = EventQueue(obj)
    elif type(obj) == _xine.Event:
        o = Event(obj)
    else:
        raise TypeError, "Unknown xine object: " + str(obj)

    obj.wrapper = weakref.ref(o)
    return o

def _debug_show_chain(o, level = 0):
    # For debugging, shows the post chain
    indent = " " * level
    if type(o) == _xine.Stream:
        print "%s [STREAM] %s " % (indent, repr(o))
        print "%s   Video:" % indent
        vt = o.video_source
        _debug_show_chain(vt, level + 5)
        print "%s   Audio:" % indent
        at = o.audio_source
        _debug_show_chain(at, level + 5)
    elif type(o) == _xine.PostIn:
        post = o.get_owner()
        print '%s  -> [POST IN %s / %s]' % (indent, post.name, o.get_name()), o
        for output in post.list_outputs():
            _debug_show_chain(post.post_output(output), level)
    elif type(o) == _xine.PostOut:
        target = o.get_port()
        if type(o.get_owner()) == _xine.Stream:
            name = "(stream)"
        else:
            name = o.get_owner().name
        print '%s  -> [POST OUT %s / %s]' % (indent, name, o.get_name()), o
        _debug_show_chain(target, level + 5)
    elif type(o) == _xine.VideoPort:
        owner = o.get_owner()
        if type(owner) != _xine.Xine:
            return _debug_show_chain(owner, level)
        print '%s  -> [VIDEO DRIVER]' % indent, o
    elif type(o) == _xine.AudioPort:
        owner = o.get_owner()
        if type(owner) != _xine.Xine:
            return _debug_show_chain(owner, level)
        print '%s  -> [AUDIO DRIVER]' % indent, o
    elif o == None:
        print '%s  -> [NONE]' % indent
    else:
        print '%s  -> [UNKNOWN]' % indent, o



class Wrapper(object):
    def __init__(self, obj):
        self._obj = obj
        self._obj.wrapper = weakref.ref(self)

    def __cmp__(self, o):
        if type(o) != type(self):
            return 1
        return cmp(self._obj, o._obj)

    def __repr__(self):
        return "<%s wrapper for object at %#x>" % (self.__class__.__name__, id(self._obj) & 0xFFFFFFFFL)



class Xine(Wrapper):
    def __init__(self, obj= None):
        if not obj:
            obj = _xine.Xine()

        obj.log_callback = notifier.WeakCallback(self._log_callback)
        self.signals = {
            "log": notifier.Signal()
        }
        super(Xine, self).__init__(obj)

    def _get_vo_display_size(self, width, height, aspect):
        if width == 0 or height == 0:
            return 0, 0, 0

        frame_aspect = width / float(height)
        if aspect == 0:
            win_aspect = frame_aspect
        else:
            win_aspect = frame_aspect * aspect

        # Calculate the requisite display size
        if frame_aspect > win_aspect:
            d_width = width
            d_height = int(math.ceil(width / win_aspect))
        else:
            d_width = int(math.ceil(height * win_aspect))
            d_height = height

        return d_width, d_height, win_aspect

    def _default_frame_output_cb(self, width, height, aspect, window):
        #print "FRAME OUTPUT CB", width, height, aspect
        w, h, a = self._get_vo_display_size(width, height, aspect)
        if aspect > 0 and abs(window._aspect - a) > 0.01:
            print "VO: %dx%d -> %dx%d" % (width, height, w, h)
            window.resize((w, h))
            window._aspect = a
        if window:
            w, h = window.get_size()

        # Return order: dst_pos, win_pos, dst_size, aspect
        return (0, 0), (0, 0), (w, h), 1.0

    def _default_dest_size_cb(self, width, height, aspect, window):
        #print "DEST SIZE CB", width, height, aspect, window.get_size()
        if not window.get_visible():
            w, h, a = self._get_vo_display_size(width, height, aspect)
        else:
            w, h = window.get_size()
        return (w, h), 1.0

    def load_video_output_plugin(self, driver = "auto", **kwargs):
        if driver in ("xv", "xshm", "opengl", "sdl", "kaa"):
            if "window" in kwargs:
                window = kwargs["window"]
                assert(isinstance(window, display.X11Window))
                if "frame_output_cb" not in kwargs:
                    kwargs["frame_output_cb"] = notifier.WeakCallback(self._default_frame_output_cb, window)
                if "dest_size_cb" not in kwargs:
                    kwargs["dest_size_cb"] = notifier.WeakCallback(self._default_dest_size_cb, window)
                window._aspect = -1
                kwargs["window"] = window._window

            if "wid" in kwargs:
                if type(kwargs["wid"]) == str and kwargs["wid"][:2] == "0x":
                    kwargs["wid"] = int(kwargs["wid"], 16)


        driver = self._obj.load_video_output_plugin(driver, **kwargs)
        return _wrap_xine_object(driver)
                    
    def open_video_driver(self, driver = "auto", **kwargs):
        if "window" not in kwargs and driver == "auto":
            driver = "none"
        driver = self.load_video_output_plugin(driver, **kwargs)
        vo = driver.get_port()
        return vo


    def open_audio_driver(self, driver = "auto", **kwargs):
        ao = self._obj.open_audio_driver(driver, **kwargs)
        return _wrap_xine_object(ao)


    def new_stream(self, audio_port = None, video_port = None):
        if audio_port == None:
            audio_port = self.open_audio_driver()
        if video_port == None:
            video_port = self.open_video_driver()

        assert(type(audio_port) == AudioPort)
        assert(type(video_port) == VideoPort)

        stream = self._obj.stream_new(audio_port._obj, video_port._obj)
        return _wrap_xine_object(stream)

    def list_video_plugins(self):
        return self._obj.list_plugins("video")

    def list_audio_plugins(self):
        return self._obj.list_plugins("audio")

    def list_post_plugins(self, types = -1):
        return self._obj.list_plugins("post", types)

    def list_demuxer_plugins(self):
        return self._obj.list_plugins("demuxer")

    def list_input_plugins(self):
        return self._obj.list_plugins("input")

    def list_spu_plugins(self):
        return self._obj.list_plugins("spu")

    def list_audio_decoder_plugins(self):
        return self._obj.list_plugins("audio_decoder")

    def list_video_decoder_plugins(self):
        return self._obj.list_plugins("video_decoder")

    def post_init(self, name, inputs = 0, audio_targets = [], video_targets = []):
        """
        This method is deprecated.  Use new_post() instead.
        """
        return self.new_post(name, inputs, audio_targets, video_targets)

    def new_post(self, name, inputs = 0, audio_targets = [], video_targets = []):
        assert(type(audio_targets) in (list, tuple))
        assert(type(video_targets) in (list, tuple))
        ao = []
        for item in audio_targets:
            if type(item) == PostIn:
                item = item.get_port()
            assert(type(item) == AudioPort)
            ao.append(item._obj)
        vo = []
        for item in video_targets:
            if type(item) == PostIn:
                item = item.get_port()
            assert(type(item) == VideoPort)
            vo.append(item._obj)

        post = self._obj.post_init(name, inputs, ao, vo)
        return _wrap_xine_object(post)

    def get_log_names(self):
        return self._obj.get_log_names()

    def _resolve_log_section_name(self, section):
        return section

    def get_log(self, section):
        if type(section) == str:
            sections = self.get_log_names()
            if section not in sections:
                raise XineError, "Unknown log section: " + section
            section = sections.index(section)
        return self._obj.get_log(section)


    def _log_callback(self, section):
        sections = self.get_log_names()
        section = sections[section]
        self.signals["log"].emit(section)
 
    def get_parameter(self, param):
        return self._obj.get_engine_param(param)

    def set_parameter(self, param, value):
        return self._obj.set_engine_param(param, value)
      
    def get_browsable_input_plugin_ids(self):
        return self._obj.get_input_plugin_ids("browsable")

    def get_browse_mrls(self, plugin, start_mrl = None):
        return self._obj.get_browse_mrls(plugin, start_mrl)

    def get_autoplay_input_plugin_ids(self):
        return self._obj.get_input_plugin_ids("autoplay")

    def get_autoplay_mrls(self, plugin):
        return self._obj.get_autoplay_mrls(plugin)

    def get_file_extensions(self):
        return self._obj.get_file_extensions().split(" ")

    def get_mime_types(self):
        types = []
        for t in self._obj.get_mime_types().split(";"):
            vals = map(lambda x: x.strip(), t.split(":"))
            if len(vals) > 1:
                vals[1] = tuple(vals[1].split(","))
            types.append(tuple(vals))
        return types

    def get_config_entries(self):
        cfg = self._obj.config_get_first_entry()
        yield cfg
        while True:
            cfg = self._obj.config_get_next_entry()
            if not cfg:
                break
            yield cfg

    def get_config_value(self, key):
        return self._obj.config_lookup_entry(key)

    def set_config_value(self, key, value):
        cfg = self.get_config_value(key)
        if cfg == None:
            raise XineError, "Config option '%s' doesn't exist" % key
        if cfg["type"] == tuple and type(value) != int:
            # Try to resolve value
            if value not in cfg["enums"]:
                raise XineError, "Value '%s' is not in list of valid values" % value
            value = cfg["enums"].index(value)
        else:
            assert(type(value) == cfg["type"])
        return self._obj.config_update_entry(key, value)


class VODriver(Wrapper):
    def __init__(self, obj):
        super(VODriver, self).__init__(obj)

    def get_port(self):
        # A new VODriver() is owned by a Xine object, but when get_port() is
        # first called, the new VideoPort assumes ownership of us.
        port = self._obj.get_port()
        return _wrap_xine_object(port)
        

class VideoPort(Wrapper):
    def __init__(self, obj):
        super(VideoPort, self).__init__(obj)

    def get_owner(self):
        # Can be Xine, Post, or Stream object
        return _wrap_xine_object(self._obj.get_owner())

    def get_driver(self):
        return _wrap_xine_object(self._obj.driver)

    def send_gui_data(self, type, data = 0):
        return self._obj.send_gui_data(type, data)

    def _get_wire_list(self):
        l = []
        for ptr in self._obj.wire_list:
            l.append(_xine.get_object_by_id(ptr))
            #l.append(_wrap_xine_object(_xine.get_object_by_id(ptr)))
        return l

class AudioPort(Wrapper):
    def __init__(self, obj):
        super(AudioPort, self).__init__(obj)

    def get_owner(self):
        # Can be Xine, Post, or Stream object
        return _wrap_xine_object(self._obj.get_owner())

    def _get_wire_list(self):
        l = []
        for ptr in self._obj.wire_list:
            l.append(_xine.get_object_by_id(ptr))
            #l.append(_wrap_xine_object(_xine.get_object_by_id(ptr)))
        return l

class Stream(Wrapper):
    def __init__(self, obj):
        super(Stream, self).__init__(obj)
        self.signals = {
            "event": notifier.Signal()
        }
        self.event_queue = self.new_event_queue()
        kaa.signals["idle"].connect_weak(self._poll_events)
        #self.event_queue._queue.event_callback = notifier.WeakCallback(self._obj_callback)

    def _poll_events(self):
        event = self.event_queue.get_event()
        if event:
            self.signals["event"].emit(_wrap_xine_object(event))

    def open(self, mrl):
        return self._obj.open(mrl)

    def play(self, time = 0.0, pos = 0):
        return self._obj.play(pos, int(time*1000))

    def get_video_source(self):
        return _wrap_xine_object(self._obj.video_source)

    def get_audio_source(self):
        return _wrap_xine_object(self._obj.audio_source)

    def slave(self, slave, affection = 0xff):
        assert(type(slave) == Stream)
        assert(slave != self)
        return self._obj.slave(slave._obj, affection)

    def set_trick_mode(self, mode, value):
        return self._obj.set_trick_mode(mode, value)

    def stop(self):
        return self._obj.stop()

    def close(self):
        return self._obj.close()

    def eject(self):
        return self._obj.eject()

    def get_current_vpts(self):
        return self._obj.get_current_vpts()

    def get_status(self):
        return self._obj.get_status()

    def get_error(self):
        return self._obj.get_error()

    def get_audio_lang(self, channel = -1):
        return self._obj.get_lang("audio", channel)

    def get_spu_lang(self, channel = -1):
        return self._obj.get_lang("spu", channel)

    def get_pos_length(self):
        pos, time, length = self._obj.get_pos_length()
        if pos == None:
            return 0, 0, 0

        return pos, time / 1000.0, length / 1000.0

    def get_stream_pos(self):
        return self.get_pos_length()[0]

    def get_time(self):
        return self.get_pos_length()[1]

    def get_length(self):
        return self.get_pos_length()[2]

    def get_info(self, info):
        return self._obj.get_info(info)

    def get_meta_info(self, info):
        return self._obj.get_meta_info(info)

    def get_parameter(self, param):
        return self._obj.get_param(param)

    def set_parameter(self, param, value):
        return self._obj.set_param(param, value)

    def _seek_thread(self, time):
        self.set_parameter(PARAM_SPEED, SPEED_NORMAL)
        if not self.get_parameter(STREAM_INFO_SEEKABLE):
            print "Stream not seekable"
            return False

        self.play(time)


    def _seek(self, time):
        if self.get_status() != STATUS_PLAY:
            print "Stream not playing"
            return False
         
        # Need a xine engine mutex for this.  Later.  
        #thread = threading.Thread(target = self._seek_thread, args = (time,))
        #thread.start()
        self._seek_thread(time)
        
    def seek_relative(self, offset):
        t = max(0, self.get_time() + offset)
        return self._seek(t)

    def seek_absolute(self, t):
        t = max(0, t)
        return self._seek(t)

    def new_event_queue(self):
        return _wrap_xine_object(self._obj.new_event_queue())


    def send_event(self, type, **kwargs):
        return self._obj.send_event(type, **kwargs)

class Post(Wrapper):
    def __init__(self, obj):
        super(Post, self).__init__(obj)

    def get_parameters_desc(self):
        return self._obj.get_parameters_desc()

    def get_parameters(self):
        params = self._obj.get_parameters()
        desc = self.get_parameters_desc()
        for key, value in params.items():
            if desc[key]["enums"]:
                params[key] = desc[key]["enums"][params[key]]

        return params

    def set_parameters(self, **kwargs):
        parms = self.get_parameters_desc()
        for key, value in kwargs.items():
            assert(key in parms)
            # Check enums for value
            if value in parms[key]["enums"]:
                value = kwargs[key] = parms[key]["enums"].index(value)
            elif parms[key]["enums"] and type(value) != parms[key]["type"]:
                raise XineError, "Value '%s' for parameter '%s' invalid." % (value, key)
            elif type(value) == int and parms[key]["type"] == float:
                value = kwargs[key] = float(value)

            assert(type(value) == parms[key]["type"])
            

        return self._obj.set_parameters(kwargs)

    def get_name(self):
        return self._obj.name

    def get_description(self):
        return self._obj.get_description()

    def get_help(self):
        return self._obj.get_help()

    def list_inputs(self):
        return self._obj.list_inputs()

    def list_outputs(self):
        return self._obj.list_outputs()

    def get_output(self, name):
        return _wrap_xine_object(self._obj.post_output(name))

    def get_input(self, name):
        return _wrap_xine_object(self._obj.post_input(name))

    def unwire(self):
        for name in self.list_outputs():
            output = self.get_output(name)
            output.unwire()

    def get_default_output(self):
        return self.get_output(self.list_outputs()[0])

    def get_default_input(self):
        return self.get_input(self.list_inputs()[0])




class PostOut(Wrapper):
    def __init__(self, obj):
        super(PostOut, self).__init__(obj)

    def wire(self, input):
        if type(input) == PostIn:
            if self._obj.get_port() == input._obj.get_port():
                return
            return self._obj.wire(input._obj)

        elif type(input) == VideoPort:
            if self._obj.get_port() == input._obj:
                return
            return self._obj.wire_video_port(input._obj)

        elif type(input) == AudioPort:
            if self._obj.get_port() == input._obj:
                return
            return self._obj.wire_audio_port(input._obj)
        else:
            raise XineError, "Unsupported wire target: " + str(type(input))


    def _get_stream_from_port(self, port):
        if not port:
            return
        for ptr in port.wire_list:
            o = _xine.get_object_by_id(ptr)
            if type(o.get_owner()) == _xine.Stream:
                return o.get_owner()
            elif type(o.get_owner()) == _xine.Post:
                for input_name in o.get_owner().list_inputs():
                    input = o.get_owner().post_input(input_name)
                    res = self._get_stream_from_port(input.get_port())
                    if res:
                        return res


    def unwire(self):
        if type(self.get_owner()) == Stream:
            #if type(self.get_port()) == VideoPort:
            # XXX: we could do this automatically ...
            raise XineError, "Can't unwire a Stream source.  Try rewiring to a null port."

        # Given previous -> me -> next, connect previous to next.  The problem
        # is that for multiple inputs/outputs this could do the wrong thing.
        # So we make a guess and use the first input/output and hope for the
        # best.  If anything more intelligent is needed, it will have to be
        # done manually.
        old_target = _wrap_xine_object(self._obj.get_port())

        # If we're here, owner is a Post.
        post = self._obj.get_owner()
        # Get the list of audio/video inputs for this post.
        inputs = [ post.post_input(x) for x in post.list_inputs() ]
        inputs = filter(lambda x: x.get_type() in (POST_DATA_AUDIO, POST_DATA_VIDEO), inputs)
        if len(inputs) > 1:
            raise XineError, "Can't automatically unwire a post with multiple inputs"

        # Get each PostOut connected to this.
        for previous_id in inputs[0].get_port().wire_list[:]:
            previous = _xine.get_object_by_id(previous_id)
            previous_port = previous.get_port()
            #print "WIRE OBJET", previous_id, previous, previous_port
            #rint "** STREAM:", self._get_stream_from_port(previous_port)
            # Wire this one to our old target.
            _wrap_xine_object(previous).wire(old_target)

        
    def get_type(self):
        # POST_DATA_VIDEO or POST_DATA_AUDIO
        return self._obj.get_type()

    def get_name(self):
        return self._obj.get_name()

    def get_owner(self):
        # Can be Post or Stream
        return _wrap_xine_object(self._obj.get_owner())

    def get_port(self):
        return _wrap_xine_object(self._obj.get_port())

    def get_wire_target(self):
        return _wrap_xine_object(self._obj.get_port())



class PostIn(Wrapper):
    def __init__(self, obj):
        super(PostIn, self).__init__(obj)

    def get_owner(self):
        # Post object
        return _wrap_xine_object(self._obj.get_owner())

    def get_type(self):
        # POST_DATA_VIDEO or POST_DATA_AUDIO
        return self._obj.get_type()

    def get_name(self):
        return self._obj.get_name()

    def get_port(self):
        return _wrap_xine_object(self._obj.get_port())


class EventQueue(Wrapper):
    def __init__(self, obj):
        super(EventQueue, self).__init__(obj)

    def get_event(self):
        return self._obj.get_event()

class Event(Wrapper):
    def __init__(self, obj):
        super(Event, self).__init__(obj)

    def __getattr__(self, attr):
        if attr in ("type", "data"):
            return getattr(self._obj, attr)
        else:
            return object.__getattr__(self, attr)

    def get_stream(self):
        return _wrap_xine_object(self._obj.get_owner().get_owner())

    def get_queue(self):
        return _wrap_xine_object(self._obj.get_owner())
