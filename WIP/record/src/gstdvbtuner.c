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

/**
 * SECTION:element-plugin
 *
 * <refsect2>
 * <title>Example launch line</title>
 * <para>
 * <programlisting>
 * gst-launch -v -m audiotestsrc ! plugin ! fakesink silent=TRUE
 * </programlisting>
 * </para>
 * </refsect2>
 */

#ifdef HAVE_CONFIG_H
#  include <config.h>
#endif

#include <gst/gst.h>

#include <assert.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <string.h>

#include "dvb/dmx.h"
#include "dvb/frontend.h"

#include "gstdvbtuner.h"


typedef struct {
	char *name;
	int value;
} Param;

static const Param inversion_list [] = {
	{ "INVERSION_OFF", INVERSION_OFF },
	{ "INVERSION_ON", INVERSION_ON },
	{ "INVERSION_AUTO", INVERSION_AUTO },
        { NULL, 0 }
};

static const Param bw_list [] = {
	{ "BANDWIDTH_6_MHZ", BANDWIDTH_6_MHZ },
	{ "BANDWIDTH_7_MHZ", BANDWIDTH_7_MHZ },
	{ "BANDWIDTH_8_MHZ", BANDWIDTH_8_MHZ },
        { NULL, 0 }
};

static const Param fec_list [] = {
	{ "FEC_1_2", FEC_1_2 },
	{ "FEC_2_3", FEC_2_3 },
	{ "FEC_3_4", FEC_3_4 },
	{ "FEC_4_5", FEC_4_5 },
	{ "FEC_5_6", FEC_5_6 },
	{ "FEC_6_7", FEC_6_7 },
	{ "FEC_7_8", FEC_7_8 },
	{ "FEC_8_9", FEC_8_9 },
	{ "FEC_AUTO", FEC_AUTO },
	{ "FEC_NONE", FEC_NONE },
        { NULL, 0 }
};

static const Param guard_list [] = {
	{"GUARD_INTERVAL_1_16", GUARD_INTERVAL_1_16},
	{"GUARD_INTERVAL_1_32", GUARD_INTERVAL_1_32},
	{"GUARD_INTERVAL_1_4", GUARD_INTERVAL_1_4},
	{"GUARD_INTERVAL_1_8", GUARD_INTERVAL_1_8},
        { NULL, 0 }
};

static const Param hierarchy_list [] = {
	{ "HIERARCHY_1", HIERARCHY_1 },
	{ "HIERARCHY_2", HIERARCHY_2 },
	{ "HIERARCHY_4", HIERARCHY_4 },
	{ "HIERARCHY_NONE", HIERARCHY_NONE },
        { NULL, 0 }
};

static const Param atsc_list [] = {
	{ "8VSB", VSB_8 },
	{ "QAM_256", QAM_256 },
	{ "QAM_64", QAM_64 },
	{ "QAM", QAM_AUTO },
        { NULL, 0 }
};

static const Param qam_list [] = {
	{ "QPSK", QPSK },
	{ "QAM_128", QAM_128 },
	{ "QAM_16", QAM_16 },
	{ "QAM_256", QAM_256 },
	{ "QAM_32", QAM_32 },
	{ "QAM_64", QAM_64 },
        { NULL, 0 }
};

static const Param transmissionmode_list [] = {
	{ "TRANSMISSION_MODE_2K", TRANSMISSION_MODE_2K },
	{ "TRANSMISSION_MODE_8K", TRANSMISSION_MODE_8K },
        { NULL, 0 }
};


GST_DEBUG_CATEGORY_STATIC (gst_dvbtuner_debug);
#define GST_CAT_DEFAULT gst_dvbtuner_debug

/* Filter signals and args */
enum
{
  /* FILL ME */
  LAST_SIGNAL
};

enum
{
  ARG_0,
  ARG_DEBUG_OUTPUT,
  ARG_ADAPTER,
  ARG_FRONTENDTYPE,
  ARG_FRONTENDNAME,
  ARG_HWDECODER,
  ARG_ERROR,
  ARG_ERRNO,
  ARG_PID_FILTER
};

/* **********************************************************************************
 * CODE FOR ARG_FRONTENDTYPE
 * ********************************************************************************** */

typedef enum {
  GST_FRONTENDTYPE_UNKNOWN,
  GST_FRONTENDTYPE_QPSK,
  GST_FRONTENDTYPE_QAM,
  GST_FRONTENDTYPE_OFDM,
  GST_FRONTENDTYPE_ATSC
} GstFrontendtypePattern;


#define GST_TYPE_FRONTENDTYPE_PATTERN (gst_frontendtype_pattern_get_type ())
static GType
gst_frontendtype_pattern_get_type (void)
{
  static GType frontendtype_pattern_type = 0;

  if (!frontendtype_pattern_type) {
    static GEnumValue pattern_types[] = {
      { GST_FRONTENDTYPE_UNKNOWN, "unknown", "unknown adapter" },
      { GST_FRONTENDTYPE_QPSK, "QPSK", "DVB-S adapter" },
      { GST_FRONTENDTYPE_QAM, "QAM", "DVB-C adapter" },
      { GST_FRONTENDTYPE_OFDM, "OFDM", "DVB-T adapter" },
      { GST_FRONTENDTYPE_ATSC, "ATSC", "DVB-A adapter" },
      { 0, NULL, NULL },
    };

    frontendtype_pattern_type =
	g_enum_register_static ("GstFrontendtypePattern",
				pattern_types);
  }

  return frontendtype_pattern_type;
}


/* **********************************************************************************++ */

GST_BOILERPLATE (GstDvbTuner, gst_dvbtuner, GstElement,
    GST_TYPE_ELEMENT);

static void gst_dvbtuner_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec);
static void gst_dvbtuner_get_property (GObject * object, guint prop_id,
    GValue * value, GParamSpec * pspec);

static gboolean gst_dvbtuner_set_caps (GstPad * pad, GstCaps * caps);
static GstFlowReturn gst_dvbtuner_chain (GstPad * pad, GstBuffer * buf);

static void
gst_dvbtuner_base_init (gpointer gclass)
{
  static GstElementDetails element_details = {
    "Tuner for DVB devices",
    "Freevo/DvbTuner",
    "Tune DVB device to specified channel",
    "Soenke Schwardt <schwardt@users.sourceforge.net>"
  };
  GstElementClass *element_class = GST_ELEMENT_CLASS (gclass);

  gst_element_class_set_details (element_class, &element_details);
}

/* initialize the plugin's class */
static void
gst_dvbtuner_class_init (GstDvbTunerClass * klass)
{
  GObjectClass *gobject_class;
  GstElementClass *gstelement_class;

  gobject_class = (GObjectClass *) klass;
  gstelement_class = (GstElementClass *) klass;

  gobject_class->set_property = gst_dvbtuner_set_property;
  gobject_class->get_property = gst_dvbtuner_get_property;

  g_object_class_install_property (gobject_class, ARG_DEBUG_OUTPUT, 
    g_param_spec_boolean ("debug-output", "DebugOutput", "Produce verbose debug output ?", 
			  FALSE, G_PARAM_READWRITE)); 

  g_object_class_install_property (gobject_class, ARG_ADAPTER, 
    g_param_spec_uint ("adapter", "Adapter", "Number of adapter", 
                       0, 1024, 0, G_PARAM_READWRITE)); 

  g_object_class_install_property (gobject_class, ARG_FRONTENDNAME,
    g_param_spec_string ("frontendname", "FrontendName", "name of frontend", 
			"", G_PARAM_READABLE)); 

  g_object_class_install_property (G_OBJECT_CLASS (klass), ARG_FRONTENDTYPE,
    g_param_spec_enum ("frontendtype", "Frontend Type",
		       "Type of frontend",
		       GST_TYPE_FRONTENDTYPE_PATTERN, 1, G_PARAM_READABLE));
}

/* initialize the new element
 * instantiate pads and add them to element
 * set functions
 * initialize structure
 */
static void
gst_dvbtuner_init (GstDvbTuner * filter,
    GstDvbTunerClass * gclass)
{
  GstElementClass *klass = GST_ELEMENT_GET_CLASS (filter);

  filter->sinkpad =
      gst_pad_new_from_template (gst_element_class_get_pad_template (klass,
          "sink"), "sink");
  gst_pad_set_setcaps_function (filter->sinkpad, gst_dvbtuner_set_caps);
  gst_pad_set_getcaps_function (filter->sinkpad, gst_pad_proxy_getcaps);

  filter->srcpad =
      gst_pad_new_from_template (gst_element_class_get_pad_template (klass,
          "src"), "src");
  gst_pad_set_getcaps_function (filter->srcpad, gst_pad_proxy_getcaps);

  gst_element_add_pad (GST_ELEMENT (filter), filter->sinkpad);
  gst_element_add_pad (GST_ELEMENT (filter), filter->srcpad);
  gst_pad_set_chain_function (filter->sinkpad, gst_dvbtuner_chain);

  /* properties */
  filter->debug_output = FALSE;
  filter->adapter = 0;
  filter->hwdecoder = FALSE;

  /* internal data */
  filter->fn_frontend_dev = NULL;
  filter->fn_demux_dev = NULL;
  filter->fn_dvr_dev = NULL;
  filter->fn_video_dev = NULL;

  gst_dvbtuner_set_new_adapter_fn(filter);
}


static void
gst_dvbtuner_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec)
{
  GstDvbTuner *filter = GST_DVBTUNER (object);

  switch (prop_id) {
  case ARG_DEBUG_OUTPUT:
    filter->debug_output = g_value_get_boolean (value);
    break;
  case ARG_ADAPTER:  
    {
      guint new_adapter = g_value_get_uint(value);
      DEBUGf("setting adapter from %d to %d\n", filter->adapter, new_adapter);
      filter->adapter = new_adapter;
      
      gst_dvbtuner_set_new_adapter_fn(filter);
      
      gst_dvbtuner_tuner_init(filter);
      break;  
    }
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    break;
  }
}

static void
gst_dvbtuner_get_property (GObject * object, guint prop_id,
    GValue * value, GParamSpec * pspec)
{
  GstDvbTuner *filter = GST_DVBTUNER (object);

  switch (prop_id) {
  case ARG_DEBUG_OUTPUT:
    g_value_set_boolean (value, filter->debug_output);
    break;
  case ARG_ADAPTER:
    g_value_set_uint (value, filter->adapter);
    break;
  case ARG_FRONTENDTYPE: 
    if (filter->fd_frontend_dev >= 0) {
      g_value_set_enum (value, filter->feinfo.type); 
    } else {
      g_value_set_enum (value, GST_FRONTENDTYPE_UNKNOWN);
    }
    break; 
  case ARG_FRONTENDNAME:
    if (filter->fn_frontend_dev && filter->feinfo.name) {
      g_value_set_string (value, filter->feinfo.name); 
    } else {
      g_value_set_string (value, "");
    }
    break; 
  default:
    G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
    break;
  }
}

/* GstElement vmethod implementations */

/* this function handles the link with other elements */
static gboolean
gst_dvbtuner_set_caps (GstPad * pad, GstCaps * caps)
{
  GstDvbTuner *filter;
  GstPad *otherpad;

  filter = GST_DVBTUNER (gst_pad_get_parent (pad));
  otherpad = (pad == filter->srcpad) ? filter->sinkpad : filter->srcpad;

  return gst_pad_set_caps (pad, caps);
}

/* chain function
 * this function does the actual processing
 */

static GstFlowReturn
gst_dvbtuner_chain (GstPad * pad, GstBuffer * buf)
{
  GstDvbTuner *filter;

  filter = GST_DVBTUNER (GST_OBJECT_PARENT (pad));

  if (filter->debug_output == FALSE)
    g_print ("I'm plugged, therefore I'm in.\n");

  /* just push out the incoming buffer without touching it */
  return gst_pad_push (filter->srcpad, buf);
}


/* entry point to initialize the plug-in
 * initialize the plug-in itself
 * register the element factories and pad templates
 * register the features
 *
 * exchange the string 'plugin' with your elemnt name
 */
static gboolean
plugin_init (GstPlugin * plugin)
{
  /* exchange the strings 'plugin' and 'Template plugin' with your
   * plugin name and description */
  GST_DEBUG_CATEGORY_INIT (gst_dvbtuner_debug, "dvbtuner",
      0, "plugin for tuning dvb devices");

  return gst_element_register (plugin, "dvbtuner",
      GST_RANK_NONE, GST_TYPE_DVBTUNER);
}

/* this is the structure that gstreamer looks for to register plugins
 *
 * exchange the strings 'plugin' and 'Template plugin' with you plugin name and
 * description
 */
GST_PLUGIN_DEFINE (GST_VERSION_MAJOR,
    GST_VERSION_MINOR,
    "freevo",
    "freevo specific plugins",
    plugin_init, VERSION, "GPL", "FreevoBinaryPackage", "http://www.freevo.org/")


/******/

static void
gst_dvbtuner_set_new_adapter_fn(GstDvbTuner *filter) {

  if (filter->fn_frontend_dev) {
    g_free(filter->fn_frontend_dev);
  }
  filter->fn_frontend_dev = g_malloc( GST_DVBTUNER_FN_MAX_LEN+1 );
  snprintf(filter->fn_frontend_dev, GST_DVBTUNER_FN_MAX_LEN, "/dev/dvb/adapter%i/frontend0", filter->adapter);

  if (filter->fn_demux_dev) {
    g_free(filter->fn_demux_dev);
  }
  filter->fn_demux_dev = g_malloc( GST_DVBTUNER_FN_MAX_LEN+1 );
  snprintf(filter->fn_demux_dev, GST_DVBTUNER_FN_MAX_LEN, "/dev/dvb/adapter%i/demux0", filter->adapter);
  
  if (filter->fn_dvr_dev) {
    g_free(filter->fn_dvr_dev);
  }
  filter->fn_dvr_dev = g_malloc( GST_DVBTUNER_FN_MAX_LEN+1 );
  snprintf(filter->fn_dvr_dev, GST_DVBTUNER_FN_MAX_LEN, "/dev/dvb/adapter%i/dvr0", filter->adapter);
  
  if (filter->fn_video_dev) {
    g_free(filter->fn_video_dev);
  }
  filter->fn_video_dev = g_malloc( GST_DVBTUNER_FN_MAX_LEN+1 );
  snprintf(filter->fn_video_dev, GST_DVBTUNER_FN_MAX_LEN, "/dev/dvb/adapter%i/video0", filter->adapter);  
}


static void
gst_dvbtuner_tuner_release(GstDvbTuner *filter) {
  DEBUGf("FIXME! NOW!\n");
  // - alle file deskriptoren schließen
  // - set status to DOWN
}


static void
gst_dvbtuner_tuner_init(GstDvbTuner *filter) {

  gst_dvbtuner_tuner_release(filter);

  assert(filter->fn_frontend_dev);

  DEBUGf( "opening frontend device\n");
  if ((filter->fd_frontend_dev = open(filter->fn_frontend_dev, O_RDWR)) < 0){
    DEBUGf( "error opening frontend device: %s\n", strerror(errno));
    gst_dvbtuner_tuner_release(filter);
    return;
  }

  DEBUGf( "getting frontend info\n");
  if ((ioctl(filter->fd_frontend_dev, FE_GET_INFO, &filter->feinfo)) < 0) {
    DEBUGf( "error getting frontend info: %s\n", strerror(errno));
    gst_dvbtuner_tuner_release(filter);
    return;
  }

  if (filter->debug_output) {
    DEBUGf("frontend '%s':  ",filter->feinfo.name);
    if(filter->feinfo.type==FE_QPSK) DEBUGf("SAT Card (DVB-S)\n");
    if(filter->feinfo.type==FE_QAM) DEBUGf("CAB Card (DVB-C)\n");
    if(filter->feinfo.type==FE_OFDM) DEBUGf("TER Card (DVB-T)\n");
    if(filter->feinfo.type==FE_ATSC) DEBUGf("US Card (?)\n");
  }
  
  if ((filter->fd_video_dev=open(filter->fn_video_dev, O_RDWR)) < 0) {
    filter->hwdecoder = FALSE;
    DEBUGf("hardware decoder absent\n");
  }else{
    filter->hwdecoder = TRUE;
    DEBUGf("hardware decoder present\n");
    close(filter->fd_video_dev);
    filter->fd_video_dev = -1;
  }
}

