#include "config.h"
#include <Python.h>

#ifdef USE_IMLIB2
#include "imlib2.h"
PyTypeObject *Image_PyObject_Type;
Imlib_Image *(*imlib_image_from_pyobject)(PyObject *pyimg);
#endif

#ifdef USE_IMLIB2_DISPLAY

#include "x11window.h"
#include "x11display.h"

PyObject *render_imlib2_image(PyObject *self, PyObject *args)
{
    X11Window_PyObject *window;
    PyObject *pyimg;
    Imlib_Image *img;
    XWindowAttributes attrs;
    int dst_x = 0, dst_y = 0, src_x = 0, src_y = 0,
        w = -1, h = -1, img_w, img_h, dither = 1, blend = 0;

    if (!Image_PyObject_Type) {
        PyErr_Format(PyExc_SystemError, "kaa-imlib2 not installed.");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "O!O!|(ii)(ii)(ii)ii", 
                &X11Window_PyObject_Type, &window, 
                Image_PyObject_Type, &pyimg, 
                &dst_x, &dst_y, &src_x, &src_y, &w, &h,
                &dither, &blend))
        return NULL;

    img = imlib_image_from_pyobject(pyimg);
    imlib_context_set_image(img);
    img_w = imlib_image_get_width();
    img_h = imlib_image_get_height();

    if (w == -1) w = img_w;
    if (h == -1) h = img_h;

    XGetWindowAttributes(window->display, window->window, &attrs);
    imlib_context_set_display(window->display);
    imlib_context_set_visual(attrs.visual);
    imlib_context_set_colormap(attrs.colormap);
    imlib_context_set_drawable(window->window);

    imlib_context_set_dither(dither);
    imlib_context_set_blend(blend);
    if (src_x == 0 && src_y == 0 && w == img_w && h == img_h)
        imlib_render_image_on_drawable(dst_x, dst_y);
    else
        imlib_render_image_part_on_drawable_at_size(src_x, src_y, w, h, dst_x,
                                dst_y, w, h);

    Py_INCREF(Py_None);
    return Py_None;
}
#else

PyObject *render_imlib2_image(PyObject *self, PyObject *args)
{
    PyErr_Format(PyExc_SystemError, "kaa-display compiled without imlib2");
    return NULL;
}

#endif
