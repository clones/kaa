import _evas, array
from _evas import EvasError
# Constants

ENGINE_BUFFER_DEPTH_ARGB32 = 0
ENGINE_BUFFER_DEPTH_BGRA32 = 1
ENGINE_BUFFER_DEPTH_RGB24 = 2
ENGINE_BUFFER_DEPTH_BGR24 = 3

PIXEL_FORMAT_NONE = 0
PIXEL_FORMAT_ARGB32 = 1
PIXEL_FORMAT_YUV420P_601 = 2

RENDER_BLEND     = 0
RENDER_BLEND_REL = 1
RENDER_COPY      = 2
RENDER_COPY_REL  = 3
RENDER_ADD       = 4
RENDER_ADD_REL   = 5
RENDER_SUB       = 6
RENDER_SUB_REL   = 7
RENDER_TINT      = 8
RENDER_TINT_REL  = 9
RENDER_MASK      = 10
RENDER_MUL       = 11

# Evas doesn't seem to use anything but NONE or GENERIC yet.
LOAD_ERROR_NONE                       = 0
LOAD_ERROR_GENERIC                    = 1
LOAD_ERROR_DOES_NOT_EXIST             = 2
LOAD_ERROR_PERMISSION_DENIED          = 3
LOAD_ERROR_RESOURCE_ALLOCATION_FAILED = 4
LOAD_ERROR_CORRUPT_FILE               = 5
LOAD_ERROR_UNKNOWN_FORMAT             = 6

def render_method_list():
    return _evas.render_method_list()


class LoadError(Exception):
    def __init__(self, errno, str = None, extra = None):
        self.data = (errno, str, extra)

    def __str__(self):
        errno, str, extra = self.data
        return "[Errno %d] %s: '%s'" % (errno, str, extra)

class TriggerList(list):
    def __init__(self, update_cb):
        self._update_cb = update_cb

    def _wrap(self, func, args):
        getattr(super(TriggerList, self), func)(*args)
        self._update_cb(self)

for f in ("__setitem__", "__delitem__", "append", "__add__", "__delslice__", 
          "__mul__", "__setslice__", "extend", "reverse", "sort", "pop", 
          "remove", "insert"):
    tmp = eval("lambda self, *args: self._wrap('%s', args)" % f)
    setattr(TriggerList, f, tmp)


def _wrap_evas_object(obj):
    if obj == None:
        return None

    obj_type = obj.type_get()
    if obj_type == "image":
        return Image(obj)
    elif obj_type == "rectangle":
        return Rectangle(obj)
    elif obj_type == "text":
        return Text(obj)
    elif obj_type == "gradient":
        return Gradient(obj)
    elif obj_type == "textblock":
        return TextBlock(obj)
    else:
        raise ValueError, "Unable to wrap unknown object type (%s)" % obj_type


class Object(object):

    def __init__(self, evas_object):
        assert type(evas_object) == _evas.Object
        self.__dict__[ "_object" ] = evas_object
        #self._object = evas_object

    def __eq__(self, other):
        if not isinstance(other, Object):
            return False
        return self._object == other._object

    def __setattr__(self, key, value):
        setattr(self._object, key, value)

    def __getattr__(self, key):
        if key in self.__dict__: #("_object"):
            return self.__dict__[key]
        exstr = "%s instance has no attribute '%s'" % \
                (self.__class__.__name__, key)
        if not hasattr(self._object, key):
            raise AttributeError, exstr
        value = getattr(self._object, key)
        if callable(value):
            raise AttributeError, exstr
        return value

    def type_get(self):
        return self._object.type_get()

    def move(self, pos):
        return self._object.move(pos)

    def resize(self, size):
        return self._object.resize(size)

    def hide(self):
        return self._object.hide()

    def show(self):
        return self._object.show()

    def geometry_get(self):
        return self._object.geometry_get()

    def evas_get(self):
        return Evas(wrap = self._object.evas_get())

    def layer_set(self, layer):
        return self._object.layer_set(layer)

    def layer_get(self):
        return self._object.layer_get()

    def visible_get(self):
        return self._object.visible_get()

    def visible_set(self, visible):
        if visible:
            self.show()
        else:
            self.hide()

    def color_get(self):
        return self._object.color_get()

    def color_set(self, r=None, g=None, b=None, a=None):
        if None in (r, g, b, a):
            def f(x, y):
                if x == None: return y
                return x
            (r, g, b, a) = map(f, (r, g, b, a), self.color_get())
        (r, g, b, a) =  map(lambda x: min(255, max(0, x)), (r, g, b, a))
        return self._object.color_set(r, g, b, a)
     
     
    def name_set(self, name):
        self._object.name_set(name)
        
    def name_get(self):
        return self._object.name_get()

    def clip_set(self, clip_object):
        self._object.clip_set(clip_object._object)

    def clip_get(self):
        o = self._object.clip_get()
        return _wrap_evas_object(o)

    def clip_unset(self):
        self._object.clip_unset()

    def clipees_get(self):
        list = []
        for o in self._object.clipees_get():
            list.append(_wrap_evas_object(o))
        return list

    def object_raise(self):
        self._object.object_raise()

    def object_lower(self):
        self._object.object_lower()

    def stack_above(self, above):
        self._object.stack_above(above._object)

    def stack_below(self, below):
        self._object.stack_above(below._object)

    def render_op_set(self, op):
        self._object.render_op_set(op)

    def render_op_get(self):
        return self._object.render_op_get()


class Rectangle(Object):
    def __init__(self, evas_object):
        super(Rectangle, self).__init__(evas_object)



class Gradient(Object):
    def __init__(self, evas_object):
        super(Gradient, self).__init__(evas_object)

    def color_add(self, r, g, b, a, distance):
        return self._object.gradient_color_add(r, g, b, a, distance)

    def colors_clear(self):
        return self._object.gradient_colors_clear()

    def angle_set(self, angle):
        return self._object.gradient_angle_set(angle)

    def angle_get(self):
        return self._object.gradient_angle_get()


class Image(Object):
    def __init__(self, evas_object):
        super(Image, self).__init__(evas_object)

    def file_set(self, filename):
        return self._object.image_file_set(filename)

    def file_get(self):
        return self._object.image_file_get()

    def fill_set(self, pos, size):
        return self._object.image_fill_set(pos, size)

    def fill_get(self):
        return self._object.image_fill_get()

    def size_set(self, size):
        return self._object.image_size_set(size)

    def size_get(self):
        return self._object.image_size_get()

    def load_error_get(self):
        return self._object.image_load_error_get()

    def load(self, filename):
        self.file_set(filename)
        err = self.load_error_get()
        if err:
            raise LoadError, (err, "Unable to load image", filename)
        size = self.size_get()
        self.fill_set( (0, 0), size )
        self.resize( size )

    def alpha_get(self):
        return self._object.image_alpha_get()

    def alpha_set(self, has_alpha):
        return self._object.image_alpha_set(has_alpha)

    def smooth_scale_set(self, smooth_scale):
        return self._object.image_smooth_scale_set(smooth_scale)

    def smooth_scale_get(self):
        return self._object.image_smooth_scale_get()

    def reload(self):
        return self._object.image_reload()

    def data_set(self, data, copy = -1):
        return self._object.image_data_set(data, copy)

    def data_get(self, for_writing = True):
        return self._object.image_data_get(for_writing)

    def data_update_add(self, x, y, w, h):
        return self._object.image_data_update_add(x, y, w, h)

    def pixels_dirty_set(self, dirty = True):
        return self._object.image_pixels_dirty_set(dirty)

    def pixels_dirty_get(self):
        return self._object.image_pixels_dirty_get()

    def pixels_import(self, data, w, h, format):
        return self._object.image_pixels_import(data, w, h, format)

    def border_set(self, l, r, t, b):
        return self._object.image_border_set(l, r, t, b)

    def border_get(self):
        return self._object.image_border_get()

    def border_center_fill_set(self, fill):
        return self._object.image_border_center_fill_set(fill)
        
    def border_center_fill_get(self):
        return self._object.image_border_center_fill_get()



class TextBlock(Object):
    def __init__(self, evas_object):
        super(TextBlock, self).__init__(evas_object)

    def markup_set(self, markup):
        return self._object.textblock_markup_set(markup)

    def markup_get(self):
        return self._object.textblock_markup_get()

    def clear(self):
        return self._object.textblock_clear()

    def style_set(self, style):
        return self._object.textblock_style_set(style)

    def size_formatted_get(self):
        return self._object.textblock_size_formatted_get()

    def size_native_get(self):
        return self._object.textblock_size_native_get()

    def style_insets_get(self):
        return self._object.textblock_style_insets_get()

    def cursor_get(self):   
        return self._object.textblock_cursor_get()

    def line_number_geometry_get(self, line):
        return self._object.textblock_line_number_geometry_get(line)

class Text(Object):
    def __init__(self, evas_object):
        super(Text, self).__init__(evas_object)

    def font_set(self, font, size):
        return self._object.text_font_set(font, size)

    def font_get(self):
        return self._object.text_font_get()

    def text_set(self, text):
        return self._object.text_text_set(text)

    def text_get(self):
        return self._object.text_text_get()

    def font_source_get(self):
        return self._object.text_font_source_get()

    def font_source_set(self, source):
        return self._object.text_font_source_set(source)

    def ascent_get(self):
        return self._object.text_ascent_get()

    def descent_get(self):
        return self._object.text_descent_get()

    def max_ascent_get(self):
        return self._object.text_max_ascent_get()

    def max_descent_get(self):
        return self._object.text_max_descent_get()

    def horiz_advance_get(self):
        return self._object.text_horiz_advance_get()

    def vert_advance_get(self):
        return self._object.text_vert_advance_get()

    def inset_get(self):
        return self._object.text_inset_get()

    # Convenience function
    def metrics_get(self):
        return {
            "ascent": self.ascent_get(),
            "descent": self.descent_get(),
            "max_ascent": self.max_ascent_get(),
            "max_descent": self.max_descent_get(),
            "horiz_advance": self.horiz_advance_get(),
            "vert_advance": self.vert_advance_get(),
            "inset": self.inset_get(),
        }

    def char_pos_get(self, pos):
        return self._object.text_char_pos_get(pos)

    def char_coords_get(self, (x, y)):
        return self._object.text_char_coords_get(x, y)

    def style_pad_get(self):
        return self._object.text_style_pad_get()


class Evas(object):
    def __init__(self, wrap = None, **kwargs):
        if wrap and type(wrap) == _evas.Evas:
            self.__dict__["_evas"] = wrap
            return

        evas = _evas.Evas()
        self.__dict__["_evas"] = evas
        self.fontpath = ["."]

    # XXX: don't implement me!  (Ref cycles can't get collected automatically)
    #def __del__(self):

    def __eq__(self, other):
        if not isinstance(other, Evas):
            return False
        return self._evas == other._evas

    def __setattr__(self, key, value):
        if key == "fontpath":
            l = TriggerList(self._evas.font_path_set)
            l.extend(value)
            value = l
        if key in ():
            # Special attributes; garbage collection is handled differently
            # than attributes assigned to the __dict__.  These are included
            # in traversal but not in clearing, because they need to be kept
            # alive during the evas dealloc.  Evas dealloc will decref these.
            setattr(self._evas, key, value)
        else:
            self._evas.__dict__[key] = value

    def __getattr__(self, key):
        if key == "_dependencies":
            return self._evas.dependencies
        if key in self.__dict__:
            return self.__dict__[key]
        if key in self._evas.__dict__:
            return self._evas.__dict__[key]
        return getattr(self._evas, key)

    def render(self):
        return self._evas.render()

    def output_size_set(self, size):
        return self._evas.output_size_set(size)

    def output_size_get(self):
        return self._evas.output_size_get()

    def viewport_set(self, pos, size):
        return self._evas.viewport_set(pos, size)

    def viewport_get(self):
        return self._evas.viewport_get()

    def image_cache_flush(self):
        return self._evas.image_cache_flush()

    def image_cache_reload(self):
        return self._evas.image_cache_reload()

    def image_cache_get(self):
        return self._evas.image_cache_get()

    def image_cache_set(self, size):
        return self._evas.image_cache_set(size)

    def object_rectangle_add(self):
        return Rectangle(self._evas.object_rectangle_add())

    def object_gradient_add(self):
        return Gradient(self._evas.object_gradient_add())

    def object_image_add(self, filename = None):
        img = Image(self._evas.object_image_add())
        if filename:
            img.load(filename)
        return img

    def object_text_add(self, (font, size) = (None, None), text = None):
        o = Text(self._evas.object_text_add())
        if font:
            o.font_set(font, size)
        if text:
            o.text_set(text)
        return o

    def object_textblock_add(self):
        return TextBlock(self._evas.object_textblock_add())
        

    def damage_rectangle_add(self, ((x, y), (w, h))):
        self._evas.damage_rectangle_add(x, y, w, h)

    def object_name_find(self, name):
        obj = self._evas.object_name_find(name)
        return _wrap_evas_object(obj)


class EvasBuffer(Evas):

    def __init__(self, size, viewport = None, **kwargs):
        super(EvasBuffer, self).__init__()

        if "depth" not in kwargs:
            kwargs["depth"] = ENGINE_BUFFER_DEPTH_BGR24
        bpp = (4, 4, 3, 3)[ kwargs["depth"] ]
        if not kwargs.get("stride"):
            kwargs["stride"] = size[0] * bpp
        if not kwargs.get("buffer"):
            kwargs["buffer"] = array.array('c', '\0'*size[0]*size[1]*bpp)
        kwargs["size"] = size
        assert type(kwargs["buffer"]) in (array.array, buffer, int)

        result = self._evas.output_set("buffer", **kwargs)
        self.output_size_set(size)
        if not viewport:
            viewport = (0, 0), size
        self.viewport_set(viewport[0], viewport[1])
        self._buffer = kwargs["buffer"]

    def buffer_get(self):
        return self._buffer


_tsc_factor = None

def benchmark_reset():
    _evas.benchmark_reset()

def benchmark_get():
    global _tsc_factor
    if not _tsc_factor:
        # Figure out the timestamp-counter-to-seconds factor.  benchmark_calibrate
        # will time a sleep (argument is in usecs) and compare the time stamp
        # counter to what gettimeofday produces, returning the ratio.  This
        # ratio is then used to convert tsc to seconds.
        s = sum([ _evas.benchmark_calibrate(10**pow) for pow in range(3, 6) ])
        _tsc_factor = (s / 3.0) * 1000000
 
    return _evas.benchmark_get() / _tsc_factor

#def new(render_method = None, size = None, viewport = None, **kwargs):
#    return Evas(render_method, size, viewport, **kwargs)
