#include <Python.h>

#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/kd.h>
#include <linux/vt.h>
#include <linux/fb.h>
#include <errno.h>

#define X_DISPLAY_MISSING
#include <Imlib2.h>

Imlib_Image *(*imlib_image_from_pyobject)(PyObject *pyimg);
PyTypeObject *Image_PyObject_Type;

int fb_fd = 0;
int *fb_mem = 0;

static struct fb_var_screeninfo fb_var;
static struct fb_fix_screeninfo fb_fix;

static void tty_disable (void);
static void tty_enable (void);

/* Copy from the supplied 32-bit ARGB to the same-structure framebuffer */
PyObject *fb_update(PyObject *self, PyObject *args)
{
  PyObject *pyimg;
  Imlib_Image *img;
  unsigned char *pixels;

  if (!PyArg_ParseTuple(args, "O!", Image_PyObject_Type, &pyimg)) {
    PyErr_Format(PyExc_SystemError, "imlib2 image as parameter needed");
    return NULL;
  }
  
  img = imlib_image_from_pyobject(pyimg);
  imlib_context_set_image(img);
  pixels = (unsigned char *)imlib_image_get_data_for_reading_only();

  memcpy(fb_mem, pixels, imlib_image_get_width() *
	 imlib_image_get_height() * 4);

   Py_INCREF(Py_None);
   return Py_None;
}


PyObject *fb_open(PyObject *self, PyObject *args)
{
  tty_disable ();
  
  fb_fd = open ("/dev/fb0", O_RDWR);
  
  if (fb_fd < 0) {
    perror ("open");
    PyErr_Format(PyExc_SystemError, "unable to open device");
    return NULL;
  }

  if (ioctl (fb_fd, FBIOGET_FSCREENINFO, &fb_fix) != 0) {
    perror ("ioctl");
    close (fb_fd);
    PyErr_Format(PyExc_SystemError, "unable to get screeninfo");
    return NULL;
  }

  if (ioctl (fb_fd, FBIOGET_VSCREENINFO, &fb_var) != 0) {
    perror ("ioctl");
    close (fb_fd);
    PyErr_Format(PyExc_SystemError, "unable to get screen vars");
    return NULL;
  }

  /* OK, this is ugly but we need this. */
  fb_var.bits_per_pixel = 32;
  
  /* try to set fbsettings */
  PyArg_ParseTuple(args, "(iiiiiiiiiiiiiiiii)", &fb_var.xres, &fb_var.yres, 
		   &fb_var.xres_virtual, &fb_var.yres_virtual, 
		   &fb_var.xoffset, &fb_var.yoffset, &fb_var.height, 
		   &fb_var.height, &fb_var.pixclock, &fb_var.left_margin, 
		   &fb_var.right_margin, &fb_var.upper_margin, 
		   &fb_var.lower_margin, &fb_var.vsync_len, 
		   &fb_var.hsync_len,
		   &fb_var.sync, &fb_var.vmode);

  if (ioctl (fb_fd, FBIOPUT_VSCREENINFO, &fb_var) != 0) {
    perror ("ioctl");
    close (fb_fd);
    PyErr_Format(PyExc_SystemError, "unable to set screen vars");
    return NULL;

  }

  if (ioctl (fb_fd, FBIOGET_VSCREENINFO, &fb_var) != 0) {
    perror ("ioctl");
    close (fb_fd);
    PyErr_Format(PyExc_SystemError, "unable to get screen vars");
    return NULL;

  }

  if (fb_var.bits_per_pixel != 32) {
    close (fb_fd);
    PyErr_Format(PyExc_SystemError, "unable to set depth=32");
    return NULL;
  }

  fb_mem = mmap ((void *) NULL, fb_var.xres * fb_var.yres * fb_var.bits_per_pixel / 8,
		 PROT_READ | PROT_WRITE, MAP_SHARED, fb_fd, 0);

  close (fb_fd);
  fb_fd = 0;
  
  if (fb_mem == MAP_FAILED) {
    perror ("mmap");
    PyErr_Format(PyExc_SystemError, "unable to get memory");
    return NULL;
  }
  Py_INCREF(Py_None);
  return Py_None;
}


PyObject *fb_close(PyObject *self, PyObject *args)
{
  tty_enable ();
  Py_INCREF(Py_None);
  return Py_None;
}

PyObject *fb_size(PyObject *self, PyObject *args)
{
  return Py_BuildValue("(ii)", fb_var.xres, fb_var.yres);
}


PyObject *fb_depth(PyObject *self, PyObject *args)
{
  return Py_BuildValue("i", fb_var.bits_per_pixel);
}

PyObject *fb_info(PyObject *self, PyObject *args)
{
  return Py_BuildValue("(iiiiiiiiiiiiiiiii)", fb_var.xres, fb_var.yres, 
		       fb_var.xres_virtual, fb_var.yres_virtual, 
		       fb_var.xoffset, fb_var.yoffset, fb_var.height, 
		       fb_var.height, fb_var.pixclock, fb_var.left_margin, 
		       fb_var.right_margin, fb_var.upper_margin, 
		       fb_var.lower_margin, fb_var.vsync_len, 
		       fb_var.hsync_len,
		       fb_var.sync, fb_var.vmode);
}

static void tty_disable (void)
{
  int tty;


  tty = open ("/dev/tty0", O_RDWR);
  if(tty < 0) {
    perror("Error can't open /dev/tty0");
    exit (1);
  }

  if(ioctl (tty, KDSETMODE, KD_GRAPHICS) == -1) {
    perror("Error setting graphics mode for tty");
    close(tty);
    exit (1);
  }
  
  close(tty);

}


static void tty_enable (void)
{
  int tty;
  
  tty = open ("/dev/tty0", O_RDWR);
  if(tty < 0) {
    perror("Error can't open /dev/tty0");
    exit (1);
  }

  if(ioctl (tty, KDSETMODE, KD_TEXT) == -1) {
    perror("Error setting text mode for tty");
    close(tty);
    exit (1);
  }
  
  close(tty);

}

PyMethodDef fb_methods[] = {
    { "open", (PyCFunction) fb_open, METH_VARARGS },
    { "close", (PyCFunction) fb_close, METH_VARARGS },
    { "update", (PyCFunction) fb_update, METH_VARARGS },
    { "size", (PyCFunction) fb_size, METH_VARARGS },
    { "depth", (PyCFunction) fb_depth, METH_VARARGS },
    { "info", (PyCFunction) fb_info, METH_VARARGS },
    { NULL }
};

void **get_module_api(char *module)
{
    PyObject *m, *c_api;
    void **ptrs;

    m = PyImport_ImportModule(module);
    if (m == NULL)
       return;
    c_api = PyObject_GetAttrString(m, "_C_API");
    if (c_api == NULL || !PyCObject_Check(c_api))
        return;
    ptrs = (void **)PyCObject_AsVoidPtr(c_api);
    Py_DECREF(c_api);
    return ptrs;
}


void init_FBmodule() {
  void **imlib2_api_ptrs;
  (void) Py_InitModule("_FBmodule", fb_methods);
  
  // Import kaa-imlib2's C api
  imlib2_api_ptrs = get_module_api("kaa.imlib2._Imlib2");
  if (imlib2_api_ptrs == NULL)
    return;
  imlib_image_from_pyobject = imlib2_api_ptrs[0];
  Image_PyObject_Type = imlib2_api_ptrs[1];
}
