/* *********************************************************************** 
 * vbi.c
 *
 * Author:   <dmeyer@tzi.de>
 *
 * $Id$
 * ********************************************************************* */

#include <Python.h>
#include <libzvbi.h>

typedef struct {
    PyObject_HEAD
    vbi_capture *cap;
    vbi_raw_decoder* par;
    vbi_sliced* sliced;
    vbi_decoder* dec;
    char *nname;
    unsigned int nuid;
} VBIPyObject;

#define VBI ((VBIPyObject *)self)

void vbi_decoder_vbi_event(vbi_event* event, void* data)
{
    switch(event->type) {
    case VBI_EVENT_NETWORK:
	if (!((VBIPyObject*) data)->nuid && strlen((const char*) event->ev.network.name)) {
	  ((VBIPyObject*) data)->nname = strdup((const char*) event->ev.network.name);
	  ((VBIPyObject*) data)->nuid = event->ev.network.nuid;
	}
        break;
    case VBI_EVENT_CAPTION:
      printf("VBI_EVENT_CAPTION\n");
      break;
    case VBI_EVENT_TTX_PAGE:
      //printf("VBI_EVENT_TTX_PAGE\n");
      break;
    case VBI_EVENT_ASPECT:
      printf("VBI_EVENT_ASPECT\n");
      break;
    case VBI_EVENT_PROG_INFO:
      printf("VBI_EVENT_PROG_INFO\n");
      break;
    default:
      printf("VBI_EVENT_UNKNOWN\n");
      break;
    }
}

static int VBIPyObject__init(VBIPyObject *self, PyObject *args)
{
  char* errorstr = NULL;
  
  unsigned int services = VBI_SLICED_VBI_525 | VBI_SLICED_VBI_625
    | VBI_SLICED_TELETEXT_B | VBI_SLICED_CAPTION_525
    | VBI_SLICED_CAPTION_625 | VBI_SLICED_VPS
    | VBI_SLICED_WSS_625 | VBI_SLICED_WSS_CPR1204;

  char *device;

  if (!PyArg_ParseTuple(args,"s", &device))
    return -1;

  self->cap = vbi_capture_v4l2_new(device, 16, &services, -1, &errorstr, 1);
  if (!self->cap) 
    return -1;
  self->par = vbi_capture_parameters(self->cap);
  if (!self->par) 
    return -1;

  self->sliced = new vbi_sliced[self->par->count[0] + self->par->count[1]];
  self->dec = vbi_decoder_new();

  vbi_event_handler_register(self->dec,
			     VBI_EVENT_NETWORK | VBI_EVENT_CAPTION |
 			     VBI_EVENT_TTX_PAGE | VBI_EVENT_ASPECT  | VBI_EVENT_PROG_INFO,
			     &vbi_decoder_vbi_event,
			     self);
  self->nname = NULL;
  self->nuid  = 0;
  return 0;
}


void VBIPyObject__dealloc(VBIPyObject *self)
{
  if (self->sliced) 
    delete[](self->sliced);
  if (self->cap) 
    vbi_capture_delete(self->cap);
  PyMem_DEL(self);
}



PyObject *VBIPyObject__read_sliced(PyObject *self, PyObject* args)
{
  double ts = 0.0;
  int lines = 2;
  timeval tv = { 1, 0 };

  switch ( vbi_capture_read_sliced(VBI->cap, VBI->sliced, &lines, &ts, &tv) ) {
  case -1:
    PyErr_Format(PyExc_RuntimeError, "read sliced failed");
    return NULL;
  case 1:
    vbi_decode(VBI->dec, VBI->sliced, lines, ts);
    break;
  default:
    break;
  }
  Py_INCREF(Py_None);
  return Py_None;
}



PyObject *VBIPyObject__reset(PyObject *self, PyObject* args)
{
  if (VBI->nname)
    free(VBI->nname);
  VBI->nname = NULL;
  VBI->nuid = 0;
  Py_INCREF(Py_None);
  return Py_None;
}


static PyMethodDef VBIPyObject__methods[] = {
  {"read_sliced", VBIPyObject__read_sliced, METH_VARARGS },
  {"reset", VBIPyObject__reset, METH_VARARGS },
  { NULL }
};


PyObject *VBIPyObject__getattr(VBIPyObject *self, char *name)
{
  if (!strcmp(name, "network")) {
    if (self->nname || self->nuid)
      return Py_BuildValue("si", self->nname, self->nuid);
    else {
      Py_INCREF(Py_None);
      return Py_None;
    }
  }
  return Py_FindMethod(VBIPyObject__methods, (PyObject *)self, name);
}


PyTypeObject VBIPyObject_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                                  /* ob_size*/
    "kaa.record.Chain",                 /* tp_name*/
    sizeof(VBIPyObject),              /* tp_basicsize*/
    0,					/* tp_itemsize*/
    (destructor)VBIPyObject__dealloc, /* tp_dealloc */
    0,					/* tp_print*/
    (getattrfunc)VBIPyObject__getattr, /* tp_getattr */
    0,					/* tp_setattr*/
    0,					/* tp_compare*/
    0,					/* tp_repr*/
    0,					/* tp_as_number*/
    0,					/* tp_as_sequence*/
    0,					/* tp_as_mapping*/
    0,					/* tp_hash */
    0,					/* tp_call*/
    0,					/* tp_str*/
    0,					/* tp_getattro*/
    0,					/* tp_setattro*/
    0,					/* tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,			/* tp_flags*/
    "Chain Object",			/* tp_doc*/
    0,					/* tp_traverse */
    0,					/* tp_clear */
    0,					/* tp_richcompare */
    0,					/* tp_weaklistoffset */
    0,					/* tp_iter */
    0,					/* tp_iternext */
    VBIPyObject__methods,		/* tp_methods */
    0,					/* tp_members */
    0,					/* tp_getset */
    0,					/* tp_base */
    0,					/* tp_dict */
    0,					/* tp_descr_get */
    0,					/* tp_descr_set */
    0,					/* tp_dictoffset */
    (initproc)VBIPyObject__init,      /* tp_init */
    0,					/* tp_alloc */
    PyType_GenericNew,			/* tp_new */
};

PyMethodDef module_methods[] = {
    { NULL }
};

extern "C"
void init_vbi() {
  PyObject *m = Py_InitModule("_vbi", module_methods);

  if (PyType_Ready(&VBIPyObject_Type) >= 0)
      PyModule_AddObject(m, "VBI", (PyObject *)&VBIPyObject_Type);

}

/* end of vbi.c */

