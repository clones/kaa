/*
 * GStreamer
 * Copyright 2005 Thomas Vander Stichele <thomas@apestaart.org>
 * Copyright 2005 Ronald S. Bultje <rbultje@ronald.bitfreak.net>
 * 
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 *
 * Alternatively, the contents of this file may be used under the
 * GNU Lesser General Public License Version 2.1 (the "LGPL"), in
 * which case the following provisions apply instead of the ones
 * mentioned above:
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef __GST_DVBTUNER_H__
#define __GST_DVBTUNER_H__

#include <sys/time.h>
#include <time.h>

#include <gst/gst.h>

G_BEGIN_DECLS

/* #defines don't like whitespacey bits */
#define GST_TYPE_DVBTUNER \
  (gst_dvbtuner_get_type())
#define GST_DVBTUNER(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST((obj),GST_TYPE_DVBTUNER,GstDvbTuner))
#define GST_DVBTUNER_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST((klass),GST_TYPE_DVBTUNER,GstDvbTunerClass))
#define GST_IS_PLUGIN_TEMPLATE(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE((obj),GST_TYPE_DVBTUNER))
#define GST_IS_PLUGIN_TEMPLATE_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_TYPE((klass),GST_TYPE_DVBTUNER))

#define DEBUGf( fmt, args... ) \
   do { \
     if (filter->debug_output) { \
       struct timeval tv;                                           \
       gettimeofday( &tv, NULL );                                   \
       struct tm *curtime;                                          \
       time_t now = time(NULL);                                     \
       curtime = localtime( &now );                                 \
       g_print( "\n%02d:%02d:%02d.%03d %10s:%04d (%s): " fmt,           \
                curtime->tm_hour, curtime->tm_min, curtime->tm_sec, ((int)tv.tv_usec / 1000),  \
                __FILE__, __LINE__, __FUNCTION__, ##args);                       \
     } \
   } while(0);


#define GST_DVBTUNER_FN_MAX_LEN  255

typedef struct _GstDvbTuner      GstDvbTuner;
typedef struct _GstDvbTunerClass GstDvbTunerClass;

struct _GstDvbTuner
{
  GstElement element;

  GstPad *sinkpad, *srcpad;

  /**************/
  /* properties */
  /**************/
  gboolean  debug_output;
  guint32   adapter; 
  gboolean  hwdecoder;

  /****************/
  /* internal data*/
  /****************/
  gchar*    fn_frontend_dev;
  gchar*    fn_demux_dev;
  gchar*    fn_dvr_dev;
  gchar*    fn_video_dev;

  gint      fd_frontend_dev;
  gint      fd_video_dev;

  struct dvb_frontend_info       feinfo;
};

struct _GstDvbTunerClass 
{
  GstElementClass parent_class;
};

GType gst_dvbtuner_get_type (void);

static void gst_dvbtuner_set_new_adapter_fn(GstDvbTuner *filter);
static void gst_dvbtuner_tuner_init(GstDvbTuner *filter);
static void gst_dvbtuner_tuner_release(GstDvbTuner *filter);

G_END_DECLS

#endif /* __GST_DVBTUNER_H__ */
