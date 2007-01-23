#include "common.h"
#ifdef HAVE_X11
#include "x11.h"
#endif
#include "kaa.h"
#include "fb.h"
#ifdef HAVE_DIRECTFB
#include "dfb.h"
#endif
#include "dummy.h"

int
driver_get_visual_info(Xine_PyObject *xine, char *driver, PyObject *kwargs, int *visual_type_return,
                       void **visual_return, driver_info_common **driver_info_return)
{
    *visual_type_return = XINE_VISUAL_TYPE_NONE;
#ifdef HAVE_X11
    if (X11Window_PyObject_Type) {
        if (!strcmp(driver, "xv") || !strcmp(driver, "xshm") || !strcmp(driver, "auto") ||
            !strcmp(driver, "opengl") || !strcmp(driver, "sdl")) {
            *visual_type_return = XINE_VISUAL_TYPE_X11;
            return x11_get_visual_info(xine, kwargs, visual_return, driver_info_return);
        }
    }
#endif
    if (!strcmp(driver, "none")) {
        *driver_info_return = 0;
        *visual_return = 0;
        return 1;
    } 
    if (!strcmp(driver, "kaa")) {
        *visual_type_return = XINE_VISUAL_TYPE_NONE; // make constant for kaa?
        return kaa_get_visual_info(xine, kwargs, visual_return, driver_info_return);
    } 
    if (!strcmp(driver, "dummy")) {
        return dummy_get_visual_info(xine, kwargs, visual_return, driver_info_return);
    } 
    if (!strcmp(driver, "vidixfb")) {
        *visual_type_return = XINE_VISUAL_TYPE_FB;
        return fb_get_visual_info(xine, kwargs, visual_return, driver_info_return);
    }
#ifdef HAVE_DIRECTFB
    if (!strcmp(driver, "DFB")) {
        *visual_type_return = XINE_VISUAL_TYPE_DFB;
        return dfb_get_visual_info(xine, kwargs, visual_return, driver_info_return);
    }
#endif
    PyErr_Format(PyExc_ValueError, "Unknown driver: %s", driver);
    return 0;
}

