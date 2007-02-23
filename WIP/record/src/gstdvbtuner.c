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

#include <stdint.h>
#include <gst/gst.h>

#include <assert.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <string.h>

#include "gstdvbtuner.h"
#include "config.h"

static void gst_dvbtuner_set_new_adapter_fn(GstDvbTuner *filter);
static void gst_dvbtuner_tuner_init(GstDvbTuner *filter);
static void gst_dvbtuner_tuner_release(GstDvbTuner *filter);
static void gst_dvbtuner_add_pid (GstDvbTuner *filter, uint pid);
static void gst_dvbtuner_remove_pid (GstDvbTuner *filter, uint pid);
static void gst_dvbtuner_clear_pids (GstDvbTuner *filter);
static void gst_dvbtuner_tune (GstDvbTuner *filter);
static gchar* gst_dvbtuner_get_status(GstDvbTuner *filter);


/* **********************************************************************************++ */

/* Filter signals and args */
enum
{
  SIGNAL_0,

  /* methods */
  SIGNAL_ADD_PID,
  SIGNAL_REMOVE_PID,
  SIGNAL_CLEAR_PIDS,
  SIGNAL_TUNE,

  /* signals */
  SIGNAL_TUNING_FINISHED,

  LAST_SIGNAL
};

enum
{
  PROP_0,

  PROP_DEBUG_OUTPUT,
  PROP_ADAPTER,
  PROP_FRONTENDTYPE,
  PROP_FRONTENDNAME,
  PROP_HWDECODER,
  PROP_STATUS,

  PROP_FREQUENCY,
  PROP_POLARISATION,
  PROP_SAT_NO,
  PROP_SYM_RATE,
  PROP_INVERSION,
  PROP_FEC,
  PROP_CODE_RATE_HIGH_PRIO,
  PROP_CODE_RATE_LOW_PRIO,
  PROP_CONSTELLATION,
  PROP_MODULATION,
  PROP_GUARD_INTERVAL,
  PROP_BANDWIDTH,
  PROP_TRANSMISSION_MODE,
  PROP_HIERARCHY,

  PROP_LAST
};

static guint gst_dvbtuner_signals[LAST_SIGNAL] = { 0 };

/* **********************************************************************************
 * CODE FOR PROP_FRONTENDTYPE
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
      { GST_FRONTENDTYPE_QAM,  "QAM",  "DVB-C adapter" },
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


/* **********************************************************************************
 * CODE FOR PROP_INVERSION
 * ********************************************************************************** */

#define GST_TYPE_INVERSION_PATTERN (gst_inversion_pattern_get_type ())
static GType
gst_inversion_pattern_get_type (void)
{
  static GType inversion_pattern_type = 0;

  if (!inversion_pattern_type) {
    static GEnumValue pattern_types[] = {
      { INVERSION_OFF,  "OFF", "OFF" },
      { INVERSION_ON,   "ON", "ON" },
      { INVERSION_AUTO, "AUTO", "AUTO" },
      { 0, NULL, NULL },
    };

    inversion_pattern_type =
	g_enum_register_static ("GstInversionPattern",
				pattern_types);
  }

  return inversion_pattern_type;
}

/* **********************************************************************************
 * CODE FOR PROP_FEC
 * ********************************************************************************** */

#define GST_TYPE_FEC_PATTERN (gst_fec_pattern_get_type ())
static GType
gst_fec_pattern_get_type (void)
{
  static GType fec_pattern_type = 0;

  if (!fec_pattern_type) {
    static GEnumValue pattern_types[] = {
      { FEC_NONE,   "NONE",  "NONE" },
      { FEC_1_2,    "1/2",   "1/2" },
      { FEC_2_3,    "2/3",   "2/3" },
      { FEC_3_4,    "3/4",   "3/4" },
      { FEC_4_5,    "4/5",   "4/5" },
      { FEC_5_6,    "5/6",   "5/6" },
      { FEC_6_7,    "6/7",   "6/7" },
      { FEC_7_8,    "7/8",   "7/8" },
      { FEC_8_9,    "8/9",   "8/9" },
      { FEC_AUTO,   "AUTO",  "AUTO" },
      { 0, NULL, NULL },
    };

    fec_pattern_type =
	g_enum_register_static ("GstFecPattern",
				pattern_types);
  }

  return fec_pattern_type;
}

/* **********************************************************************************
 * CODE FOR PROP_MODULATION
 * ********************************************************************************** */

#define GST_TYPE_QAM_PATTERN (gst_qam_pattern_get_type ())
static GType
gst_qam_pattern_get_type (void)
{
  static GType qam_pattern_type = 0;

  if (!qam_pattern_type) {
    static GEnumValue pattern_types[] = {
      { QPSK,       "QPSK",      "QPSK" },
      { QAM_16,     "QAM_16",    "QAM_16" },
      { QAM_32,     "QAM_32",    "QAM_32" },
      { QAM_64,     "QAM_64",    "QAM_64" },
      { QAM_128,    "QAM_128",   "QAM_128" },
      { QAM_256,    "QAM_256",   "QAM_256" },
      { QAM_AUTO,   "QAM_AUTO",  "QAM_AUTO" },
      { VSB_8,      "VSB_8",     "VSB_8" },
      { VSB_16,     "VSB_16",    "VSB_16" },
      { 0, NULL, NULL },
    };

    qam_pattern_type =
	g_enum_register_static ("GstQamPattern",
				pattern_types);
  }

  return qam_pattern_type;
}

/* **********************************************************************************
 * CODE FOR PROP_GUARD_INTERVAL
 * ********************************************************************************** */

#define GST_TYPE_GUARD_PATTERN (gst_guard_pattern_get_type ())
static GType
gst_guard_pattern_get_type (void)
{
  static GType guard_pattern_type = 0;

  if (!guard_pattern_type) {
    static GEnumValue pattern_types[] = {
      { GUARD_INTERVAL_1_32,   "1/32",  "1/32" },
      { GUARD_INTERVAL_1_16,   "1/16",  "1/16" },
      { GUARD_INTERVAL_1_8,    "1/8",   "1/8" },
      { GUARD_INTERVAL_1_4,    "1/4",   "1/4" },
      { GUARD_INTERVAL_AUTO,   "AUTO",  "AUTO" },
      { 0, NULL, NULL },
    };

    guard_pattern_type =
	g_enum_register_static ("GstGuardPattern",
				pattern_types);
  }

  return guard_pattern_type;
}

/* **********************************************************************************
 * CODE FOR PROP_TRANSMISSION_MODE
 * ********************************************************************************** */

#define GST_TYPE_TRANSMISSION_MODE_PATTERN (gst_transmission_mode_pattern_get_type ())
static GType
gst_transmission_mode_pattern_get_type (void)
{
  static GType transmission_mode_pattern_type = 0;

  if (!transmission_mode_pattern_type) {
    static GEnumValue pattern_types[] = {
      { TRANSMISSION_MODE_2K,    "2K",    "2K" },
      { TRANSMISSION_MODE_8K,    "8K",    "8K" },
      { TRANSMISSION_MODE_AUTO,  "AUTO",  "AUTO" },
      { 0, NULL, NULL },
    };

    transmission_mode_pattern_type =
	g_enum_register_static ("GstTransmissionModePattern",
				pattern_types);
  }

  return transmission_mode_pattern_type;
}

/* **********************************************************************************
 * CODE FOR PROP_BANDWIDTH
 * ********************************************************************************** */

#define GST_TYPE_BANDWIDTH_PATTERN (gst_bandwidth_pattern_get_type ())
static GType
gst_bandwidth_pattern_get_type (void)
{
  static GType bandwidth_pattern_type = 0;

  if (!bandwidth_pattern_type) {
    static GEnumValue pattern_types[] = {
      { BANDWIDTH_8_MHZ,   "8_MHZ",  "8_MHZ" },
      { BANDWIDTH_7_MHZ,   "7_MHZ",  "7_MHZ" },
      { BANDWIDTH_6_MHZ,   "6_MHZ",  "6_MHZ" },
      { BANDWIDTH_AUTO,    "AUTO",   "AUTO" },
      { 0, NULL, NULL },
    };

    bandwidth_pattern_type =
	g_enum_register_static ("GstBandwidthPattern",
				pattern_types);
  }

  return bandwidth_pattern_type;
}

/* **********************************************************************************
 * CODE FOR PROP_HIERARCHY
 * ********************************************************************************** */

#define GST_TYPE_HIERARCHY_PATTERN (gst_hierarchy_pattern_get_type ())
static GType
gst_hierarchy_pattern_get_type (void)
{
  static GType hierarchy_pattern_type = 0;

  if (!hierarchy_pattern_type) {
    static GEnumValue pattern_types[] = {
      { HIERARCHY_NONE, "NONE", "NONE" },
      { HIERARCHY_1,    "1",    "1" },
      { HIERARCHY_2,    "2",    "2" },
      { HIERARCHY_4,    "4",    "4" },
      { HIERARCHY_AUTO, "AUTO", "AUTO" },
      { 0, NULL, NULL },
    };

    hierarchy_pattern_type =
	g_enum_register_static ("GstHierarchyPattern",
				pattern_types);
  }

  return hierarchy_pattern_type;
}


/* **********************************************************************************++ */

GST_BOILERPLATE (GstDvbTuner, gst_dvbtuner, GstElement,
    GST_TYPE_ELEMENT);

static void gst_dvbtuner_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec);
static void gst_dvbtuner_get_property (GObject * object, guint prop_id,
    GValue * value, GParamSpec * pspec);

/* static gboolean gst_dvbtuner_set_caps (GstPad * pad, GstCaps * caps); */
/* static GstFlowReturn gst_dvbtuner_chain (GstPad * pad, GstBuffer * buf); */

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

  g_object_class_install_property (gobject_class, PROP_DEBUG_OUTPUT,
    g_param_spec_boolean ("debug-output", "DebugOutput", "Produce verbose debug output?",
			  FALSE, G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, PROP_ADAPTER,
    g_param_spec_uint ("adapter", "Adapter", "Number of adapter",
                       0, 1024, 0, G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, PROP_FRONTENDNAME,
    g_param_spec_string ("frontendname", "FrontendName", "name of frontend",
			"", G_PARAM_READABLE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_FRONTENDTYPE,
    g_param_spec_enum ("frontendtype", "Frontend Type",
		       "Type of frontend",
		       GST_TYPE_FRONTENDTYPE_PATTERN, 1, G_PARAM_READABLE));

  g_object_class_install_property (gobject_class, PROP_HWDECODER,
    g_param_spec_boolean ("hwdecoder", "HardwareDecoder", "Is a hardware decoder present?",
			  FALSE, G_PARAM_READABLE));

  g_object_class_install_property (gobject_class, PROP_STATUS,
    g_param_spec_string ("status", "FrontendStatus", "current frontend status",
			 "", G_PARAM_READABLE));

  g_object_class_install_property (gobject_class, PROP_FREQUENCY,
    g_param_spec_uint ("frequency", "Frequency", "frequency of channel",
                       0, G_MAXUINT, 0, G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, PROP_POLARISATION,
    g_param_spec_boolean ("polarisation", "Polarisation", "polarisation (true=H ; false=V)",
                       FALSE, G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, PROP_SAT_NO,
    g_param_spec_uint ("sat-no", "SatNo", "FIXME SatNo",
                       0, G_MAXUINT, 0, G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, PROP_SYM_RATE,
    g_param_spec_uint ("symbol-rate", "Symbol-rate", "FIXME symbol-rate",
                       0, G_MAXUINT, 0, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_INVERSION,
    g_param_spec_enum ("inversion", "Inversion",  "FIXME inversion",
		       GST_TYPE_INVERSION_PATTERN, 1, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_FEC,
    g_param_spec_enum ("fec", "Fec",  "FIXME fec",
		       GST_TYPE_FEC_PATTERN, 1, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_CODE_RATE_HIGH_PRIO,
    g_param_spec_enum ("code-rate-high-prio", "CodeRateHighPrio",  "FIXME code rate high prio",
		       GST_TYPE_FEC_PATTERN, 1, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_CODE_RATE_LOW_PRIO,
    g_param_spec_enum ("code-rate-low-prio", "CodeRateLowPrio",  "FIXME code rate low prio",
		       GST_TYPE_FEC_PATTERN, 1, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_CONSTELLATION,
    g_param_spec_enum ("constellation", "Constellation",  "FIXME Constellation",
		       GST_TYPE_QAM_PATTERN, 1, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_MODULATION,
    g_param_spec_enum ("modulation", "Modulation",  "FIXME Modulation",
		       GST_TYPE_QAM_PATTERN, 1, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_GUARD_INTERVAL,
    g_param_spec_enum ("guard-interval", "GuardInterval",  "guard interval",
		       GST_TYPE_GUARD_PATTERN, 1, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_BANDWIDTH,
    g_param_spec_enum ("bandwidth", "Bandwidth",  "bandwidth",
		       GST_TYPE_BANDWIDTH_PATTERN, 1, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_TRANSMISSION_MODE,
    g_param_spec_enum ("transmission-mode", "TransmissionMode",  "transmission mode",
		       GST_TYPE_TRANSMISSION_MODE_PATTERN, 1, G_PARAM_READWRITE));

  g_object_class_install_property (G_OBJECT_CLASS (klass), PROP_HIERARCHY,
    g_param_spec_enum ("hierarchy", "Hierarchy",  "FIXME hierarchy",
		       GST_TYPE_HIERARCHY_PATTERN, 1, G_PARAM_READWRITE));

  gst_dvbtuner_signals[SIGNAL_ADD_PID] =
    g_signal_new ("add-pid",                                       /* signal name */
		  G_TYPE_FROM_CLASS (klass),                       /* itype */
		  G_SIGNAL_RUN_LAST,                               /* signal flags */
		  G_STRUCT_OFFSET (GstDvbTunerClass, add_pid),     /* class closure */
		  NULL,                                            /* accumulator */
		  NULL,                                            /* accu_data */
		  g_cclosure_marshal_VOID__INT,                    /* c_marshaller */
		  G_TYPE_NONE,                                     /* return type */
		  1,                                               /* n_params */
		  G_TYPE_INT);                                     /* param types */

  gst_dvbtuner_signals[SIGNAL_REMOVE_PID] =
    g_signal_new ("remove-pid",                                    /* signal name */
		  G_TYPE_FROM_CLASS (klass),                       /* itype */
		  G_SIGNAL_RUN_LAST,                               /* signal flags */
		  G_STRUCT_OFFSET (GstDvbTunerClass, remove_pid),  /* class closure */
		  NULL,                                            /* accumulator */
		  NULL,                                            /* accu_data */
		  g_cclosure_marshal_VOID__INT,                    /* c_marshaller */
		  G_TYPE_NONE,                                     /* return type */
		  1,                                               /* n_params */
		  G_TYPE_INT);                                     /* param types */

  gst_dvbtuner_signals[SIGNAL_CLEAR_PIDS] =
    g_signal_new ("clear-pids",                                    /* signal name */
		  G_TYPE_FROM_CLASS (klass),                       /* itype */
		  G_SIGNAL_RUN_LAST,                               /* signal flags */
		  G_STRUCT_OFFSET (GstDvbTunerClass, clear_pids),  /* class closure */
		  NULL,                                            /* accumulator */
		  NULL,                                            /* accu_data */
		  g_cclosure_marshal_VOID__VOID,                   /* c_marshaller */
		  G_TYPE_NONE,                                     /* return type */
		  0);                                              /* n_params */

  gst_dvbtuner_signals[SIGNAL_TUNE] =
    g_signal_new ("tune",                                          /* signal name */
		  G_TYPE_FROM_CLASS (klass),                       /* itype */
		  G_SIGNAL_RUN_LAST,                               /* signal flags */
		  G_STRUCT_OFFSET (GstDvbTunerClass, tune),        /* class closure */
		  NULL,                                            /* accumulator */
		  NULL,                                            /* accu_data */
		  g_cclosure_marshal_VOID__VOID,                   /* c_marshaller */
		  G_TYPE_NONE,                                     /* return type */
		  0);                                              /* n_params */

  klass->add_pid = GST_DEBUG_FUNCPTR (gst_dvbtuner_add_pid);
  klass->remove_pid = GST_DEBUG_FUNCPTR (gst_dvbtuner_remove_pid);
  klass->clear_pids = GST_DEBUG_FUNCPTR (gst_dvbtuner_clear_pids);
  klass->tune = GST_DEBUG_FUNCPTR (gst_dvbtuner_tune);
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
  int i;

/*   GstElementClass *klass = GST_ELEMENT_GET_CLASS (filter); */

/*   filter->sinkpad = */
/*       gst_pad_new_from_template (gst_element_class_get_pad_template (klass, */
/*           "sink"), "sink"); */
/*   gst_pad_set_setcaps_function (filter->sinkpad, gst_dvbtuner_set_caps); */
/*   gst_pad_set_getcaps_function (filter->sinkpad, gst_pad_proxy_getcaps); */

/*   filter->srcpad = */
/*       gst_pad_new_from_template (gst_element_class_get_pad_template (klass, */
/*           "src"), "src"); */
/*   gst_pad_set_getcaps_function (filter->srcpad, gst_pad_proxy_getcaps); */

/*   gst_element_add_pad (GST_ELEMENT (filter), filter->sinkpad); */
/*   gst_element_add_pad (GST_ELEMENT (filter), filter->srcpad); */
/*   gst_pad_set_chain_function (filter->sinkpad, gst_dvbtuner_chain); */

  /* properties */
  filter->debug_output = FALSE;
  filter->adapter = 0;
  filter->hwdecoder = FALSE;

  /* internal data */
  filter->fn_frontend_dev = NULL;
  filter->fn_demux_dev = NULL;
  filter->fn_dvr_dev = NULL;
  filter->fn_video_dev = NULL;

  filter->fd_frontend_dev = -1;
  filter->fd_video_dev = -1;

  /* init pid filter list */
  filter->pidlist.array = g_malloc( sizeof(GstDvbTunerPidListEntry) * GST_DVBTUNER_INIT_PIDLIST_LEN );
  for(i = 0; i < GST_DVBTUNER_INIT_PIDLIST_LEN; ++i) {
    filter->pidlist.array[i].pid = -1;
    filter->pidlist.array[i].fd = -1;
  }
  filter->pidlist.cnt = 4;
  filter->pidlist.free = 4;

  filter->hor_polarisation = FALSE;
  filter->sat_no = 0;
  filter->tone = 0;

  gst_dvbtuner_set_new_adapter_fn(filter);
}


static void
gst_dvbtuner_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec)
{
  GstDvbTuner *filter = GST_DVBTUNER (object);

  /* check frontend unspecific properties */
  switch (prop_id) {
  case PROP_DEBUG_OUTPUT:
    {
      filter->debug_output = g_value_get_boolean (value);
      break;
    }
  case PROP_ADAPTER:
    {
      guint new_adapter = g_value_get_uint(value);
      DEBUGf("setting adapter from %d to %d", filter->adapter, new_adapter);
      filter->adapter = new_adapter;

      gst_dvbtuner_set_new_adapter_fn(filter);

      gst_dvbtuner_tuner_init(filter);
      break;
    }
  default:
    {
      /* check frontend specific properties */
      switch(filter->feinfo.type) {
      case FE_QPSK:
	{
	  switch (prop_id) {
	  case PROP_FREQUENCY:
	    {
	      filter->feparam.frequency = g_value_get_uint(value);
	      if(filter->feparam.frequency > 11700000) {
		filter->feparam.frequency = (filter->feparam.frequency - 10600000);
		filter->tone = 1;
	      } else {
		filter->feparam.frequency = (filter->feparam.frequency - 9750000);
		filter->tone = 0;
	      }
	      filter->feparam.inversion = INVERSION_AUTO;
	      break;
	    }

	  case PROP_POLARISATION:
	    {
	      filter->hor_polarisation = g_value_get_boolean (value);
	      break;
	    }

	  case PROP_SAT_NO:
	    {
	      filter->sat_no = g_value_get_uint(value);
	      break;
	    }

	  case PROP_SYM_RATE:
	    {
	      /* FIXME: adjust value (multiply with 1000) or not? */
	      filter->feparam.u.qpsk.symbol_rate = g_value_get_uint(value) * 1000;
	      filter->feparam.u.qpsk.fec_inner = FEC_AUTO;
	      break;
	    }

	  default:
	    {
	      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
	      break;
	    }
	  }
	  break;
	}

      case FE_QAM:
	{
	  switch (prop_id) {
	  case PROP_FREQUENCY:
	    {
	      filter->feparam.frequency = g_value_get_uint(value);
	      break;
	    }

	  case PROP_INVERSION:
	    {
	      filter->feparam.inversion = g_value_get_enum (value);
	      break;
	    }

	  case PROP_SYM_RATE:
	    {
	      filter->feparam.u.qam.symbol_rate = g_value_get_uint(value);
	      break;
	    }

	  case PROP_FEC:
	    {
	      filter->feparam.u.qam.fec_inner = g_value_get_enum (value);
	      break;
	    }

	  case PROP_MODULATION:
	    {
	      filter->feparam.u.qam.modulation = g_value_get_enum (value);
	      break;
	    }

	  default:
	    {
	      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
	      break;
	    }
	  }
	  break;
	}

      case FE_OFDM:
	{
	  switch (prop_id) {
	  case PROP_FREQUENCY:
	    {
	      filter->feparam.frequency = g_value_get_uint(value);
	      if (filter->feparam.frequency < 1000000) {
		filter->feparam.frequency *= 1000;
	      }
	      break;
	    }

	  case PROP_INVERSION:
	    {
	      filter->feparam.inversion = g_value_get_enum (value);
	      break;
	    }

	  case PROP_BANDWIDTH:
	    {
	      filter->feparam.u.ofdm.bandwidth = g_value_get_enum(value);
	      break;
	    }

	  case PROP_CODE_RATE_HIGH_PRIO:
	    {
	      filter->feparam.u.ofdm.code_rate_HP = g_value_get_enum(value);
	      break;
	    }

	  case PROP_CODE_RATE_LOW_PRIO:
	    {
	      filter->feparam.u.ofdm.code_rate_LP = g_value_get_enum(value);
	      break;
	    }

	  case PROP_CONSTELLATION:
	    {
	      filter->feparam.u.ofdm.constellation = g_value_get_enum(value);
	      break;
	    }

	  case PROP_TRANSMISSION_MODE:
	    {
	      filter->feparam.u.ofdm.transmission_mode = g_value_get_enum(value);
	      break;
	    }

	  case PROP_GUARD_INTERVAL:
	    {
	      filter->feparam.u.ofdm.guard_interval = g_value_get_enum(value);
	      break;
	    }

	  case PROP_HIERARCHY:
	    {
	      filter->feparam.u.ofdm.hierarchy_information = g_value_get_enum(value);
	      break;
	    }

	  default:
	    {
	      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
	      break;
	    }
	  }
	  break;
	}

      case FE_ATSC:
	{
	  switch (prop_id) {
	  case PROP_FREQUENCY:
	    {
	      filter->feparam.frequency = g_value_get_uint(value);
	      break;
	    }

	  case PROP_MODULATION:
	    {
	      filter->feparam.u.vsb.modulation = g_value_get_enum(value);
	      break;
	    }

	  default:
	    {
	      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
	      break;
	    }
	  }
	  break;
	}
      }
    }
  }
}

static void
gst_dvbtuner_get_property (GObject * object, guint prop_id,
    GValue * value, GParamSpec * pspec)
{
  GstDvbTuner *filter = GST_DVBTUNER (object);

  /* check frontend unspecific properties */
  switch (prop_id) {
  case PROP_DEBUG_OUTPUT:
    {
      g_value_set_boolean (value, filter->debug_output);
      break;
    }

  case PROP_ADAPTER:
    {
      g_value_set_uint (value, filter->adapter);
      break;
    }

  case PROP_FRONTENDTYPE:
    {
      if (filter->fd_frontend_dev >= 0) {
	g_value_set_enum (value, filter->feinfo.type);
      } else {
	g_value_set_enum (value, GST_FRONTENDTYPE_UNKNOWN);
      }
      break;
    }

  case PROP_FRONTENDNAME:
    {
      if (filter->fn_frontend_dev && filter->feinfo.name) {
	g_value_set_string (value, filter->feinfo.name);
      } else {
	g_value_set_string (value, "");
      }
      break;
    }

  case PROP_HWDECODER:
    {
      g_value_set_boolean (value, filter->hwdecoder);
      break;
    }

  case PROP_STATUS:
    {
      gchar *txt = gst_dvbtuner_get_status(filter);
      g_value_set_string (value, txt);
      g_free(txt);
      break;
    }

  default:
    {
      /* check frontend specific properties */
      switch(filter->feinfo.type) {
      case FE_QPSK:
	{
	  switch (prop_id) {
	  case PROP_FREQUENCY:
	    {
	      if (filter->tone) {
		g_value_set_uint(value, (filter->feparam.frequency/1000) + 10600 );
	      } else {
		g_value_set_uint(value, (filter->feparam.frequency/1000) + 9750 );
	      }
	      break;
	    }

	  case PROP_POLARISATION:
	    {
	      g_value_set_boolean (value, filter->hor_polarisation);
	      break;
	    }

	  case PROP_SAT_NO:
	    {
	      g_value_set_uint (value, filter->sat_no);
	      break;
	    }

	  case PROP_SYM_RATE:
	    {
	      /* FIXME: adjust value (multiply with 1000) or not? */
	      g_value_set_uint (value, filter->feparam.u.qpsk.symbol_rate/1000);
	      break;
	    }

	  default:
	    {
	      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
	      break;
	    }
	  }
	  break;
	}

      case FE_QAM:
	{
	  switch (prop_id) {
	  case PROP_FREQUENCY:
	    {
	      g_value_set_uint (value, filter->feparam.frequency);
	      break;
	    }

	  case PROP_INVERSION:
	    {
	      g_value_set_enum (value, filter->feparam.inversion);
	      break;
	    }

	  case PROP_SYM_RATE:
	    {
	      g_value_set_uint (value, filter->feparam.u.qam.symbol_rate);
	      break;
	    }

	  case PROP_FEC:
	    {
	      g_value_set_uint (value, filter->feparam.u.qam.fec_inner);
	      break;
	    }

	  case PROP_MODULATION:
	    {
	      g_value_set_enum (value, filter->feparam.u.qam.modulation);
	      break;
	    }

	  default:
	    {
	      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
	      break;
	    }
	  }
	  break;
	}

      case FE_OFDM:
	{
	  switch (prop_id) {
	  case PROP_FREQUENCY:
	    {
	      g_value_set_uint (value, filter->feparam.frequency);
	      break;
	    }

	  case PROP_INVERSION:
	    {
	      g_value_set_enum (value, filter->feparam.inversion);
	      break;
	    }

	  case PROP_BANDWIDTH:
	    {
	      g_value_set_enum (value, filter->feparam.u.ofdm.bandwidth);
	      break;
	    }

	  case PROP_CODE_RATE_HIGH_PRIO:
	    {
	      g_value_set_enum (value, filter->feparam.u.ofdm.code_rate_HP);
	      break;
	    }

	  case PROP_CODE_RATE_LOW_PRIO:
	    {
	      g_value_set_enum (value, filter->feparam.u.ofdm.code_rate_LP);
	      break;
	    }

	  case PROP_CONSTELLATION:
	    {
	      g_value_set_enum (value, filter->feparam.u.ofdm.constellation);
	      break;
	    }

	  case PROP_TRANSMISSION_MODE:
	    {
	      g_value_set_enum (value, filter->feparam.u.ofdm.transmission_mode);
	      break;
	    }

	  case PROP_GUARD_INTERVAL:
	    {
	      g_value_set_enum (value, filter->feparam.u.ofdm.guard_interval);
	      break;
	    }

	  case PROP_HIERARCHY:
	    {
	      g_value_set_enum (value, filter->feparam.u.ofdm.hierarchy_information);
	      break;
	    }

	  default:
	    {
	      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
	      break;
	    }
	  }
	  break;
	}

      case FE_ATSC:
	{
	  switch (prop_id) {
	  case PROP_FREQUENCY:
	    {
	      g_value_set_uint (value, filter->feparam.frequency);
	      break;
	    }

	  case PROP_MODULATION:
	    {
	      g_value_set_enum (value, filter->feparam.u.vsb.modulation);
	      break;
	    }

	  default:
	    {
	      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
	      break;
	    }
	  }
	  break;
	}
      }
    }
  }
}

/******/

static void
gst_dvbtuner_set_new_adapter_fn(GstDvbTuner *filter)
{
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
gst_dvbtuner_tuner_release(GstDvbTuner *filter)
{
  if (filter->fd_frontend_dev != -1) {
    close(filter->fd_frontend_dev);
    filter->fd_frontend_dev = -1;
  }

  if (filter->fd_video_dev != -1) {
    close(filter->fd_video_dev);
    filter->fd_video_dev = -1;
  }

  DEBUGf("FIXME! NOW!");
  // - alle file deskriptoren schließen
  // - set status to DOWN
}


static void
gst_dvbtuner_tuner_init(GstDvbTuner *filter)
{

  gst_dvbtuner_tuner_release(filter);

  assert(filter->fn_frontend_dev);

  DEBUGf( "opening frontend device");
  if ((filter->fd_frontend_dev = open(filter->fn_frontend_dev, O_RDWR)) < 0) {
    DEBUGf( "error opening frontend device: %s", strerror(errno));
    gst_dvbtuner_tuner_release(filter);
    return;
  }
  if ((fcntl(filter->fd_frontend_dev, F_SETFL, O_NONBLOCK)) < 0) {
    DEBUGf( "setting frontend device to nonblock failed: %s", strerror(errno));
    gst_dvbtuner_tuner_release(filter);
    return;
  }

  DEBUGf( "getting frontend info");
  if ((ioctl(filter->fd_frontend_dev, FE_GET_INFO, &filter->feinfo)) < 0) {
    DEBUGf( "error getting frontend info: %s", strerror(errno));
    gst_dvbtuner_tuner_release(filter);
    return;
  }

  if (filter->debug_output) {
    DEBUGf("frontend '%s':  ",filter->feinfo.name);
    if(filter->feinfo.type==FE_QPSK) DEBUGf("SAT Card (DVB-S)");
    if(filter->feinfo.type==FE_QAM) DEBUGf("CAB Card (DVB-C)");
    if(filter->feinfo.type==FE_OFDM) DEBUGf("TER Card (DVB-T)");
    if(filter->feinfo.type==FE_ATSC) DEBUGf("US Card (?)");
  }

  if ((filter->fd_video_dev=open(filter->fn_video_dev, O_RDWR)) < 0) {
    filter->hwdecoder = FALSE;
    DEBUGf("hardware decoder absent");
  }else{
    filter->hwdecoder = TRUE;
    DEBUGf("hardware decoder present");
    close(filter->fd_video_dev);
    filter->fd_video_dev = -1;
  }
}


static void
gst_dvbtuner_add_pid (GstDvbTuner *filter, uint pid)
{
  int i;

  DEBUGf("adding pid %d", pid);

  /* check if already added */
  for(i=0; i<filter->pidlist.cnt; ++i) {
    if (filter->pidlist.array[i].pid == pid) {
      DEBUGf("pid %d already added", pid);
      return;
    }
  }

  /* request more mempry if needed */
  if (filter->pidlist.free == 0) {
    DEBUGf("no free space (cnt=%d/free=%d) - requesting more memory",
	   filter->pidlist.cnt, filter->pidlist.free);

    gint oldsize = filter->pidlist.cnt;
    filter->pidlist.cnt += 5;
    filter->pidlist.array = g_realloc( filter->pidlist.array, sizeof(GstDvbTunerPidListEntry) * filter->pidlist.cnt );
    assert(filter->pidlist.array);
    filter->pidlist.free += 5;
    for(i=oldsize; i<filter->pidlist.cnt; ++i) {
      filter->pidlist.array[i].pid = -1;
      filter->pidlist.array[i].fd = -1;
    }
  }

  /* add new pid and fd */
  i = 0;
  while((i < filter->pidlist.cnt) && (filter->pidlist.array[i].pid != -1)) {
    DEBUGf("i=%d  pidlist.cnt=%d  array[%d].pid=%d", i, filter->pidlist.cnt, i, filter->pidlist.array[i].pid);
    i += 1;
  }
  assert(filter->pidlist.array[i].pid == -1);
  filter->pidlist.array[i].fd = open(filter->fn_demux_dev, O_RDWR);
  /* open returns -1 in case of an error */
  if (filter->pidlist.array[i].fd != -1) {
    DEBUGf("adding pid %d", pid);

    filter->pidlist.array[i].pid = pid;
    filter->pidlist.free -= 1;

    struct dmx_pes_filter_params M;

    M.pid      = pid;
    M.input    = DMX_IN_FRONTEND;
    M.output   = DMX_OUT_TS_TAP;
    M.pes_type = DMX_PES_OTHER;
    M.flags    = DMX_IMMEDIATE_START;

    DEBUGf( "ioctl(%d, DMX_SET_PES_FILTER)  pid=%d",
	    filter->pidlist.array[i].fd, filter->pidlist.array[i].pid);
    if (ioctl(filter->pidlist.array[i].fd, DMX_SET_PES_FILTER, &M) < 0) {
      g_warning("ioctl failed: %s", strerror(errno));
    }
  }
}


static void
gst_dvbtuner_remove_pid (GstDvbTuner *filter, uint pid)
{
  int i;
  for(i=0; i<filter->pidlist.cnt; ++i) {
    if (filter->pidlist.array[i].pid == pid) {

      DEBUGf( "ioctl(%d, DMX_STOP)  pid=%d",
	      filter->pidlist.array[i].fd, filter->pidlist.array[i].pid);
      ioctl(filter->pidlist.array[i].fd, DMX_STOP);
      close(filter->pidlist.array[i].fd);

      filter->pidlist.array[i].pid = -1;
      filter->pidlist.array[i].fd = -1;

      filter->pidlist.free += 1;
      DEBUGf("new pidlist stat: cnt=%d free=%d",
	     filter->pidlist.cnt, filter->pidlist.free);
      return;
    }
  }
}


static void
gst_dvbtuner_clear_pids (GstDvbTuner *filter)
{
  int i;
  for(i=0; i<filter->pidlist.cnt; ++i) {
    if (filter->pidlist.array[i].pid != -1) {
      gst_dvbtuner_remove_pid( filter, filter->pidlist.array[i].pid );
    }
  }
}


static gint
gst_dvbtuner_set_diseqc(GstDvbTuner *filter)
{
  /* returns 0 on success and -1 on failure */

  struct dvb_diseqc_master_cmd cmd = {{0xe0, 0x10, 0x38, 0xf0, 0x00, 0x00}, 4};

  DEBUGf("sat_no=%d  tone=%d  pol=%d",
	 filter->sat_no, filter->tone, filter->hor_polarisation);


  cmd.msg[3] = 0xf0 | ((filter->sat_no * 4) & 0x0f) | (filter->tone ? 1 : 0) | (filter->hor_polarisation ? 0 : 2);

  if (ioctl(filter->fd_frontend_dev, FE_SET_TONE, SEC_TONE_OFF) < 0) {
    g_warning( "FE_SET_TONE: failed");
    return -1;
  }

  if (ioctl(filter->fd_frontend_dev, FE_SET_VOLTAGE,
	    filter->hor_polarisation ? SEC_VOLTAGE_13 : SEC_VOLTAGE_18) < 0) {
    g_warning( "FE_SET_VOLTAGE: failed");
    return -1;
  }

  usleep(15000);
  if (ioctl(filter->fd_frontend_dev, FE_DISEQC_SEND_MASTER_CMD, &cmd) < 0) {
    g_warning( "FE_DISEQC_SEND_MASTER_CMD: failed");
    return -1;
  }

  usleep(15000);
  if (ioctl(filter->fd_frontend_dev, FE_DISEQC_SEND_BURST,
	    (filter->sat_no / 4) % 2 ? SEC_MINI_B : SEC_MINI_A) < 0) {
    g_warning( "FE_DISEQC_SEND_BURST: failed");
    return -1;
  }

  usleep(15000);
  if (ioctl(filter->fd_frontend_dev, FE_SET_TONE,
	    filter->tone ? SEC_TONE_ON : SEC_TONE_OFF) < 0) {
    g_warning( "FE_SET_TONE: failed");
    return -1;
  }

   return 0;
}


static void
gst_dvbtuner_tune(GstDvbTuner *filter)
{
  struct dvb_frontend_event event;

  DEBUGf( "freq=%d  satno=%d  tone=%d  pol=%d",
	  filter->feparam.frequency,
	  filter->sat_no,
	  filter->tone,
	  filter->hor_polarisation
	  );

  if (filter->feinfo.type==FE_QPSK) {
    if (gst_dvbtuner_set_diseqc(filter) < 0) {
      return;
    }
  }

  switch (filter->feinfo.type) {
      
  case FE_QPSK:
      DEBUGf( "front_param.frequency          = %d", filter->feparam.frequency);
      DEBUGf( "front_param.inversion          = %d", filter->feparam.inversion);
      DEBUGf( "front_param.qpsk.symbol_rate   = %d", filter->feparam.u.qpsk.symbol_rate );
      DEBUGf( "front_param.qpsk.fec_inner     = %d", filter->feparam.u.qpsk.fec_inner );
      break;

  case FE_OFDM:
      DEBUGf( "front_param.frequency          = %d", filter->feparam.frequency);
      DEBUGf( "front_param.inversion          = %d", filter->feparam.inversion);
      DEBUGf( "front_param.ofdm.bandwidth     = %d", filter->feparam.u.ofdm.bandwidth );
      DEBUGf( "front_param.ofdm.code_rate_HP  = %d", filter->feparam.u.ofdm.code_rate_HP );
      DEBUGf( "front_param.ofdm.code_rate_LP  = %d", filter->feparam.u.ofdm.code_rate_LP );
      DEBUGf( "front_param.ofdm.constellation = %d", filter->feparam.u.ofdm.constellation );
      DEBUGf( "front_param.ofdm.transmission_m= %d", filter->feparam.u.ofdm.transmission_mode );
      DEBUGf( "front_param.ofdm.guard_interval= %d", filter->feparam.u.ofdm.guard_interval );
      DEBUGf( "front_param.ofdm.hierarchy_info= %d", filter->feparam.u.ofdm.hierarchy_information );
      break;
      
  default:
      DEBUGf( "FIXME: print debug output" );
  }

  /* discard stale events */
  while (ioctl(filter->fd_frontend_dev, FE_GET_EVENT, &event) != -1);

  DEBUGf("about to set frontend parameters\n");
  if (ioctl(filter->fd_frontend_dev, FE_SET_FRONTEND, &filter->feparam) < 0) {
    g_warning("ioctl(%d, FE_SET_FRONTEND, feparam) failed: %s",
	      filter->fd_frontend_dev, strerror(errno));
  }

  return;
}


static gchar*
gst_dvbtuner_get_status(GstDvbTuner *filter)
{
  gchar *txt = g_malloc(8192);
  fe_status_t status;
  uint16_t snr, signal;
  uint32_t ber, uncorrected_blocks;

  if (filter->fd_frontend_dev < 0 ) {

    snprintf(txt, 8191, "FRONTEND NOT READY");

  } else {

    snprintf(txt, 8191, "ERROR");

    if (ioctl(filter->fd_frontend_dev, FE_READ_STATUS, &status) < 0) {
      g_warning("FE_READ_STATUS failed: %s", strerror(errno));
      return txt;
    }
    if (ioctl(filter->fd_frontend_dev, FE_READ_SIGNAL_STRENGTH, &signal) < 0) {
      g_warning("FE_READ_SIGNAL_STRENGTH failed: %s", strerror(errno));
      return txt;
    }
    if (ioctl(filter->fd_frontend_dev, FE_READ_SNR, &snr) < 0) {
      g_warning("FE_READ_SNR failed: %s", strerror(errno));
      return txt;
    }
    if (ioctl(filter->fd_frontend_dev, FE_READ_BER, &ber) < 0) {
      g_warning("FE_READ_BER failed: %s", strerror(errno));
      return txt;
    }
    if (ioctl(filter->fd_frontend_dev, FE_READ_UNCORRECTED_BLOCKS, &uncorrected_blocks) < 0) {
      g_warning("FE_READ_UNCORRECTED_BLOCKS failed: %s", strerror(errno));
      return txt;
    }

    snprintf(txt, 8191, "status: %d%s%s%s%s%s%s signalstrength: %d snr: %d ber: %d unc: %d",
	     status,
	     (status & FE_HAS_SIGNAL ? " FE_HAS_SIGNAL" : ""),
	     (status & FE_TIMEDOUT   ? " FE_TIMEDOUT"   : ""),
	     (status & FE_HAS_LOCK   ? " FE_HAS_LOCK"   : ""),
	     (status & FE_HAS_CARRIER? " FE_HAS_CARRIER": ""),
	     (status & FE_HAS_VITERBI? " FE_HAS_VITERBI": ""),
	     (status & FE_HAS_SYNC   ? " FE_HAS_SYNC"   : ""),
	     signal,snr, ber, uncorrected_blocks );
  }

  // DEBUGf( "%s", txt );

  return txt;
}
