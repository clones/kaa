/* -*- coding: iso-8859-1 -*-
 * ----------------------------------------------------------------------------
 * dfb.py - DirectFB Display
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.display - Generic Display Module
 * Copyright (C) 2005, 2006 Dirk Meyer, Jason Tackaberry
 *
 * First Edition: Dirk Meyer <dmeyer@tzi.de>
 * Maintainer:    Dirk Meyer <dmeyer@tzi.de>
 * Maintainer:    Rob Shortt <rob@tvcentric.com>
 *
 * Please see the file AUTHORS for a complete list of authors.
 *
 * This library is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License version
 * 2.1 as published by the Free Software Foundation.
 *
 * This library is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
 * 02110-1301 USA
 *
 * ------------------------------------------------------------------------- */

#include <Python.h>

#include <directfb/directfb.h>

#include "config.h"
#include "common.h"

#ifdef ENABLE_ENGINE_DIRECTFB
#include <Evas.h>
#include <Evas_Engine_DirectFB.h>
PyTypeObject *Evas_PyObject_Type = NULL;
Evas *(*evas_object_from_pyobject)(PyObject *pyevas);
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


/* open dfb and create base surface */
PyObject *dfb_open(PyObject *self, PyObject *args, PyObject *keywds)
{
    int width, height;
    int layer_id = DLID_PRIMARY;
    int window_id = -1;

    static char *kwlist[] = { "width", "height", "layer_id", "window_id", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, keywds, "ii|ii", kwlist, 
                                     &width, &height, &layer_id, &window_id))
        return NULL;

    /* create the super interface */
    DFBCHECK(DirectFBInit(NULL, NULL), "DirectFBInit");

    DFBCHECK(DirectFBCreate(&dfb), "DirectFBCreate");
    dfb->SetCooperativeLevel(dfb, DFSCL_FULLSCREEN);

    DFBCHECK(dfb->GetDisplayLayer(dfb, layer_id, &layer), 
             "GetDisplayLayer");
    layer->GetConfiguration(layer, &layer_config);

    /* get the primary surface, i.e. the surface of the primary layer we have
     * exclusive access to */
    memset(&dsc, 0, sizeof(DFBSurfaceDescription));
    dsc.flags = DSDESC_CAPS | DSDESC_WIDTH | DSDESC_HEIGHT | DSDESC_PIXELFORMAT;
    layer_config.width = width;
    layer_config.height = height;

    dsc.width = layer_config.width;
    dsc.height = layer_config.height;
    dsc.pixelformat = DSPF_ARGB;

    if(layer_id == DLID_PRIMARY)
        dsc.caps = DSCAPS_PRIMARY;
    else
        dsc.caps = DSCAPS_NONE;

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


#ifdef ENABLE_ENGINE_DIRECTFB
PyObject *new_evas_dfb(PyObject *self, PyObject *args, PyObject *kwargs)
{
    Evas_Engine_Info_DirectFB *einfo;
    PyObject *evas_pyobject;
    Evas *evas;

    CHECK_EVAS_PYOBJECT

    if (!PyArg_ParseTuple(args, "O!", Evas_PyObject_Type, &evas_pyobject))
        return NULL;

    evas = evas_object_from_pyobject(evas_pyobject);

    evas_output_method_set(evas, evas_render_method_lookup("directfb"));
    einfo = (Evas_Engine_Info_DirectFB *)evas_engine_info_get(evas);
    if (!einfo) {
        PyErr_Format(PyExc_SystemError, "Evas is not built with DirectFB support.");
        return NULL;
    }

    printf("surface %dx%d\n", layer_config.width, layer_config.height);

    evas_output_size_set(evas, layer_config.width, layer_config.height);
    evas_output_viewport_set(evas, 0, 0, layer_config.width, 
                             layer_config.height);

    /* the following is specific to the engine */
    einfo->info.dfb = dfb;
    einfo->info.surface = primary;
    einfo->info.flags = DSDRAW_BLEND;
    evas_engine_info_set(evas, (Evas_Engine_Info *) einfo);

    Py_INCREF(Py_None);
    return Py_None;
}
#endif  // ENABLE_ENGINE_DIRECTFB

PyMethodDef dfb_methods[] = {
    { "open", (PyCFunction) dfb_open, METH_VARARGS | METH_KEYWORDS },
    { "close", (PyCFunction) dfb_close, METH_VARARGS },
    { "size", (PyCFunction) dfb_size, METH_VARARGS },
#ifdef ENABLE_ENGINE_DIRECTFB
    { "new_evas_dfb", (PyCFunction) new_evas_dfb, METH_VARARGS | METH_KEYWORDS },
#endif
    { NULL }
};


void init_DFBmodule(void) {
    (void) Py_InitModule("_DFBmodule", dfb_methods);

#ifdef ENABLE_ENGINE_DIRECTFB
{
    // Import kaa-evas's C api
    void **evas_api_ptrs = get_module_api("kaa.evas._evas");
    if (evas_api_ptrs != NULL) {
        evas_object_from_pyobject = evas_api_ptrs[0];
        Evas_PyObject_Type = evas_api_ptrs[1];
    } else
        PyErr_Clear();
}
#endif

}
