/* -*- coding: iso-8859-1 -*-
 * ----------------------------------------------------------------------------
 * dfb.py - DirectFB Display
 * ----------------------------------------------------------------------------
 * $Id: fb.c 1041 2005-12-27 19:06:37Z dmeyer $
 *
 * ----------------------------------------------------------------------------
 * kaa-display - X11/SDL Display module
 * Copyright (C) 2005 Dirk Meyer, Jason Tackaberry
 *
 * First Edition: Dirk Meyer <dmeyer@tzi.de>
 * Maintainer:    Dirk Meyer <dmeyer@tzi.de>
 *
 * Please see the file doc/CREDITS for a complete list of authors.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MER-
 * CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
 * Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 *
 * ------------------------------------------------------------------------- */

#include <Python.h>

#include <directfb/directfb.h>

#include "config.h"

#ifdef ENABLE_ENGINE_DFB
#include "Evas.h"
#include "Evas_Engine_DirectFB.h"
#endif

/* macro for a safe call to DirectFB functions */
#define DFBCHECK(err, err_string) \
          if (err != DFB_OK) {                                        \
	       PyErr_Format(PyExc_SystemError, err_string);           \
               return NULL;                                           \
          }

/* DFB stuff */
IDirectFB             *dfb = NULL;
IDirectFBSurface      *primary = NULL;
IDirectFBDisplayLayer *layer = NULL;
DFBSurfaceDescription  dsc;
DFBDisplayLayerConfig  layer_config;

#ifdef ENABLE_ENGINE_DFB
/* Evas stuff */
PyTypeObject *Evas_PyObject_Type;
Evas *(*evas_object_from_pyobject)(PyObject *pyevas);
#endif

/* open dfb and create base surface */
PyObject *dfb_open(PyObject *self, PyObject *args)
{
    int width, height;

    if (!PyArg_ParseTuple(args, "(ii)", &width, &height))
        return NULL;

    /* create the super interface */
    DFBCHECK(DirectFBInit(NULL, NULL), "DirectFBInit");

    DFBCHECK(DirectFBCreate(&dfb), "DirectFBCreate");
    dfb->SetCooperativeLevel(dfb, DFSCL_FULLSCREEN);

    DFBCHECK(dfb->GetDisplayLayer(dfb, DLID_PRIMARY, &layer), "GetDisplayLayer");
    layer->GetConfiguration(layer, &layer_config);

    /* get the primary surface, i.e. the surface of the primary layer we have
     * exclusive access to */
    memset(&dsc, 0, sizeof(DFBSurfaceDescription));
    dsc.flags = DSDESC_CAPS | DSDESC_WIDTH | DSDESC_HEIGHT;
    layer_config.width = width;
    layer_config.height = height;

    dsc.width = layer_config.width;
    dsc.height = layer_config.height;
    dsc.caps = DSCAPS_PRIMARY;

    DFBCHECK(dfb->CreateSurface(dfb, &dsc, &primary), "CreateSurface");

    /*
       We only have one layer and we use just like this. Most of the other
       logic is in evas, so maybe this is all we need to do
    */
    Py_INCREF(Py_None);
    return Py_None;
}

/* close directfb */
PyObject *dfb_close(PyObject *self, PyObject *args)
{
    printf("DirectFB close\n");
    layer->Release(layer);
    primary->Release(primary);
    dfb->Release(dfb);

    Py_INCREF(Py_None);
    return Py_None;
}

PyObject *dfb_size(PyObject *self, PyObject *args)
{
    return Py_BuildValue("(ii)", layer_config.width, layer_config.height);
}


#ifdef ENABLE_ENGINE_DFB
PyObject *new_evas_dfb(PyObject *self, PyObject *args, PyObject *kwargs)
{
    Evas_Engine_Info_DirectFB *einfo;
    PyObject *evas_pyobject;
    Evas *evas;

    if (!PyArg_ParseTuple(args, "O!", Evas_PyObject_Type, &evas_pyobject))
        return NULL;

    evas = evas_object_from_pyobject(evas_pyobject);

    evas_output_method_set(evas, evas_render_method_lookup("directfb"));
    einfo = (Evas_Engine_Info_DirectFB *)evas_engine_info_get(evas);
    if (!einfo) {
        PyErr_Format(PyExc_SystemError, "Unable to initialize DFB canvas");
        return NULL;
    }

    printf("surface %dx%d\n", layer_config.width, layer_config.height);

    evas_output_size_set(evas, layer_config.width, layer_config.height);
    evas_output_viewport_set(evas, 0, 0, layer_config.width, layer_config.height);

    /* the following is specific to the engine */
    einfo->info.dfb = dfb;
    einfo->info.surface = primary;
    einfo->info.flags = DSDRAW_BLEND;
    evas_engine_info_set(evas, (Evas_Engine_Info *) einfo);

    Py_INCREF(Py_None);
    return Py_None;
}
#endif  // ENABLE_ENGINE_DFB

PyMethodDef dfb_methods[] = {
    { "open", (PyCFunction) dfb_open, METH_VARARGS },
    { "close", (PyCFunction) dfb_close, METH_VARARGS },
    { "size", (PyCFunction) dfb_size, METH_VARARGS },
#ifdef ENABLE_ENGINE_DFB
    { "new_evas_dfb", (PyCFunction) new_evas_dfb, METH_VARARGS | METH_KEYWORDS },
#endif
    { NULL }
};

void **get_module_api(char *module)
{
    PyObject *m, *c_api;
    void **ptrs;

    m = PyImport_ImportModule(module);
    if (m == NULL)
	return NULL;
    c_api = PyObject_GetAttrString(m, "_C_API");
    if (c_api == NULL || !PyCObject_Check(c_api))
        return NULL;
    ptrs = (void **)PyCObject_AsVoidPtr(c_api);
    Py_DECREF(c_api);
    return ptrs;
}


void init_DFBmodule() {
    void **imlib2_api_ptrs, **evas_api_ptrs;
    (void) Py_InitModule("_DFBmodule", dfb_methods);

#ifdef ENABLE_ENGINE_DFB
    // Import kaa-evas's C api
    evas_api_ptrs = get_module_api("kaa.evas._evas");
    if (evas_api_ptrs == NULL)
        return;
    evas_object_from_pyobject = evas_api_ptrs[0];
    Evas_PyObject_Type = evas_api_ptrs[1];
#else
    Evas_PyObject_Type = NULL;
#endif

}
