/*
 * ----------------------------------------------------------------------------
 * GStreamer DVB Tuner
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.record - Recording Module based on GStreamer
 * Copyright (C) 2007 Sönke Schwardt, Dirk Meyer
 *
 * First Edition: Sönke Schwardt <bulk@schwardtnet.de>
 * Maintainer:    Sönke Schwardt <bulk@schwardtnet.de>
 *
 * Please see the file AUTHORS for a complete list of authors.
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

#ifndef __GST_DVBTUNER_H__
#define __GST_DVBTUNER_H__

#include <sys/time.h>
#include <time.h>
#include <stdint.h>

#include <gst/gst.h>

#include "dvb/dmx.h"
#include "dvb/frontend.h"

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


#define GST_DVBTUNER_FN_MAX_LEN          255
#define GST_DVBTUNER_INIT_PIDLIST_LEN    5

typedef struct _GstDvbTuner      GstDvbTuner;
typedef struct _GstDvbTunerClass GstDvbTunerClass;
typedef struct _PidList          GstDvbTunerPidList;
typedef struct _GstDvbTunerClass GstDvbTunerPidListEntry;


struct _PidListEntry
{
  gint   pid;
  gint   fd;
};


struct _PidList
{
  gint           cnt;
  gint           free;
  struct _PidListEntry  *array;
};


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

  GstDvbTunerPidList  pidlist;

  gboolean  hor_polarisation;
  guint32   sat_no;
  gint      tone;

  struct dvb_frontend_info       feinfo;
  struct dvb_frontend_parameters feparam;
};

struct _GstDvbTunerClass
{
  GstElementClass parent_class;

  void          (*add_pid)          (GstDvbTuner *filter, uint pid);
  void          (*remove_pid)       (GstDvbTuner *filter, uint pid);
  void          (*clear_pids)       (GstDvbTuner *filter);
  void          (*tune)             (GstDvbTuner *filter);
};

GType gst_dvbtuner_get_type (void);

G_END_DECLS

#endif /* __GST_DVBTUNER_H__ */
