/*
 * ----------------------------------------------------------------------------
 * mng.c
 * ----------------------------------------------------------------------------
 * $Id: mng.c 979 2005-12-14 16:09:02Z tack $
 *
 * ----------------------------------------------------------------------------
 * kaa-canvas - Canvas module
 * Copyright (C) 2005 Jason Tackaberry
 *
 * First Edition: Jason Tackaberry <tack@sault.org>
 * Maintainer:    Jason Tackaberry <tack@sault.org>
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
 * ----------------------------------------------------------------------------
 */
#include <Python.h>
#include "mng.h"
#include "structmember.h"

extern PyTypeObject MNG_PyObject_Type;

static mng_ptr 
_mng_alloc(mng_uint32 size)
{
    return (mng_ptr)calloc(1, size);
}

static void 
_mng_free(mng_ptr p, mng_uint32 size)
{
    free(p);
}


static mng_bool 
_mng_open_stream(mng_handle mng)
{
    return MNG_TRUE;
}

static mng_bool 
_mng_close_stream(mng_handle mng)
{
    return MNG_TRUE;
}


static mng_bool 
_mng_read_stream(mng_handle mng, mng_ptr buffer, mng_uint32 size, mng_uint32 *bytesread)
{
    MNG_PyObject *self = (MNG_PyObject *)mng_get_userdata(mng);
    int len = size;
    if (self->mng_data_pos + len > self->mng_data_len)
        len = self->mng_data_len - self->mng_data_pos;

    memcpy(buffer, self->mng_data + self->mng_data_pos, len);
    *bytesread = len;
    self->mng_data_pos += len;
    return MNG_TRUE;
}

static mng_bool 
_mng_process_header(mng_handle mng, mng_uint32 width, mng_uint32 height)
{
    MNG_PyObject *self = (MNG_PyObject *)mng_get_userdata(mng);

    if (self->buffer)
        free(self->buffer);
    self->buffer = malloc(width*height*4);
    self->width = width;
    self->height = height;

    mng_set_canvasstyle(mng, MNG_CANVAS_BGRA8);
    return MNG_TRUE;
}

static mng_ptr 
_mng_get_canvas_line(mng_handle mng, mng_uint32 line)
{
    MNG_PyObject *self = (MNG_PyObject *)mng_get_userdata(mng);
    return self->buffer + self->width * 4 * line;
}

static mng_uint32 
_mng_get_ticks(mng_handle mng)
{
    struct timeval tv;
    struct timezone tz;
    gettimeofday(&tv, &tz);
    return (tv.tv_sec * 1000) + (tv.tv_usec / 1000);
}

static mng_bool 
_mng_refresh(mng_handle mng, mng_uint32 x, mng_uint32 y, mng_uint32 w, mng_uint32 h)
{
    MNG_PyObject *self = (MNG_PyObject *)mng_get_userdata(mng);

    PyObject *args, *result;
    args = Py_BuildValue("(iiii)", x, y, w, h);
    result = PyEval_CallObject(self->refresh_callback, args);
    Py_DECREF(args);
    if (result) {
        Py_DECREF(result);
    }

    return MNG_TRUE;
}

static mng_bool 
_mng_set_timer(mng_handle mng, mng_uint32 msecs)
{
    MNG_PyObject *self = (MNG_PyObject *)mng_get_userdata(mng);
    self->frame_delay = msecs;
    return MNG_TRUE;
}

static mng_bool 
_mng_error(mng_handle mng, mng_int32 code, mng_int8 severity,
           mng_chunkid chunktype, mng_uint32 chunkseq,
           mng_int32 extra1, mng_int32 extra2, mng_pchar text)
{
    char chunk[5];

    chunk[0] = (char)((chunktype >> 24) & 0xFF);
    chunk[1] = (char)((chunktype >> 16) & 0xFF);
    chunk[2] = (char)((chunktype >>  8) & 0xFF);
    chunk[3] = (char)((chunktype      ) & 0xFF);
    chunk[4] = '\0';

    PyErr_Format(PyExc_SystemError, "Error playing MNG chunk (%s:%d): %s", chunk, chunkseq, text);
    return MNG_TRUE;
}


PyObject *
MNG_PyObject__new(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    MNG_PyObject *self;
    PyObject *refresh_callback;

    if (!PyArg_ParseTuple(args, "O", &refresh_callback))
        return NULL;

    if (!PyCallable_Check(refresh_callback)) {
        PyErr_Format(PyExc_ValueError, "Argument must be callable");
        return 0;
    }

    self = (MNG_PyObject *)type->tp_alloc(type, 0);

    self->refresh_callback = refresh_callback;
    Py_INCREF(self->refresh_callback);
    self->mng = mng_initialize(self, _mng_alloc, _mng_free, MNG_NULL);
    if (!self->mng)
        return 0;

    mng_setcb_errorproc(self->mng, _mng_error);
    mng_setcb_openstream(self->mng, _mng_open_stream);
    mng_setcb_closestream(self->mng, _mng_close_stream);
    mng_setcb_readdata(self->mng, _mng_read_stream);
    mng_setcb_gettickcount(self->mng, _mng_get_ticks);
    mng_setcb_settimer(self->mng, _mng_set_timer);
    mng_setcb_processheader(self->mng, _mng_process_header);
    mng_setcb_getcanvasline(self->mng, _mng_get_canvas_line);
    mng_setcb_refresh(self->mng, _mng_refresh);

    return (PyObject *)self;
}

static int
MNG_PyObject__init(MNG_PyObject *self, PyObject *args, PyObject *kwargs)
{
    return 0;
}

void
MNG_PyObject__dealloc(MNG_PyObject *self)
{
    if (self->mng_data)
        free(self->mng_data);
    if (self->mng)
        mng_cleanup(&self->mng);
    Py_DECREF(self->refresh_callback);
    self->ob_type->tp_free((PyObject*)self);
}

PyObject *
MNG_PyObject__open(MNG_PyObject * self, PyObject * args)
{
    char *mng_data;
    int len;
    if (!PyArg_ParseTuple(args, "s#", &mng_data, &len))
        return NULL;

    if (self->mng_data)
        free(self->mng_data);
    self->mng_data = malloc(len);
    memcpy(self->mng_data, mng_data, len);
    self->mng_data_len = len;
    self->mng_data_pos = 0;

    mng_readdisplay(self->mng);
    return Py_BuildValue("(iiii)", self->width, self->height, self->frame_delay, self->buffer);
}

PyObject *
MNG_PyObject__update(MNG_PyObject * self, PyObject * args)
{
    self->frame_delay = 0;
    mng_display_resume(self->mng);
    if (PyErr_Occurred())
        return NULL;

    return Py_BuildValue("i", self->frame_delay);
}

PyMethodDef MNG_PyObject_methods[] = {
    { "open", ( PyCFunction ) MNG_PyObject__open, METH_VARARGS },
    { "update", ( PyCFunction ) MNG_PyObject__update, METH_VARARGS },
    { NULL, NULL }
};


static PyMemberDef MNG_PyObject_members[] = {
    {NULL}  /* Sentinel */
};


PyTypeObject MNG_PyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "MNG",                     /*tp_name*/
    sizeof(MNG_PyObject),      /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)MNG_PyObject__dealloc, /* tp_dealloc */
    0,                         /*tp_print*/
    0,                         /*tp_getattr */
    0,                         /*tp_setattr */
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    PyObject_GenericGetAttr,   /*tp_getattro*/
    PyObject_GenericSetAttr,   /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "MNG Object",              /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    MNG_PyObject_methods,      /* tp_methods */
    MNG_PyObject_members,      /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)MNG_PyObject__init,      /* tp_init */
    0,                         /* tp_alloc */
    MNG_PyObject__new,   /* tp_new */
};

PyMethodDef mng_methods[] = {
    { NULL }
};

void init_mng()
{
    PyObject *m;

    m =  Py_InitModule("_mng", mng_methods);
    if (PyType_Ready(&MNG_PyObject_Type) < 0)
        return;
    Py_INCREF(&MNG_PyObject_Type);
    PyModule_AddObject(m, "MNG", (PyObject *)&MNG_PyObject_Type);
}
