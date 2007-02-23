/*
 * ----------------------------------------------------------------------------
 * GStreamer Transport Stream Splitter
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

#include <assert.h>
#include <string.h>
#include <glib-object.h>

#include <gst/gst.h>

#include "gsttssplitter.h"

static void gst_tssplitter_set_filter(GstTSSplitter *filter, char *name, char* pidlist);
static void gst_tssplitter_remove_filter(GstTSSplitter *filter, char *name);

/* Filter signals and args */
enum
{
  SIGNAL_0,

  /* methods */
  SIGNAL_SET_FILTER,
  SIGNAL_REMOVE_FILTER,

  /* signals */
  SIGNAL_NEW_PID_FOUND,

  LAST_SIGNAL
};

enum
{
  PROP_0,
  PROP_DEBUG_OUTPUT,
  PROP_SIGNAL_NEW_PIDS,
  PROP_LAST
};

static guint gst_tssplitter_signals[LAST_SIGNAL] = { 0 };


static GstStaticPadTemplate sink_factory = GST_STATIC_PAD_TEMPLATE ("sink",
								    GST_PAD_SINK,
								    GST_PAD_ALWAYS,
								    GST_STATIC_CAPS ("ANY")
								    );


static GstStaticPadTemplate src_factory = GST_STATIC_PAD_TEMPLATE ("src", 
								   GST_PAD_SRC, 
								   GST_PAD_REQUEST, 
								   GST_STATIC_CAPS ("ANY") 
								   );

/* **********************************************************************************++ */


#ifdef G_ENABLE_DEBUG
#define g_marshal_value_peek_string(v) (char*) g_value_get_string (v)
#else /* !G_ENABLE_DEBUG */
#define g_marshal_value_peek_string(v) (v)->data[0].v_pointer
#endif

void
  marshal_VOID__STRING_STRING (GClosure *closure,
			       GValue *return_value,
			       guint n_param_values,
			       const GValue *param_values,
			       gpointer invocation_hint,
			       gpointer marshal_data)
{
  typedef void (*GMarshalFunc_VOID__STRING_STRING) (gpointer data1,
						    gpointer arg_1,
						    gpointer arg_2,
						    gpointer data2);
  register GMarshalFunc_VOID__STRING_STRING callback;
  register GCClosure *cc = (GCClosure*) closure;
  register gpointer data1, data2;
 
  g_return_if_fail (n_param_values == 3);
 
  if (G_CCLOSURE_SWAP_DATA (closure))
    {
      data1 = closure->data;
      data2 = g_value_peek_pointer (param_values + 0);
    }
  else
    {
      data1 = g_value_peek_pointer (param_values + 0);
      data2 = closure->data;
    }
  callback = (GMarshalFunc_VOID__STRING_STRING) (marshal_data ? marshal_data : cc->callback);
 
  callback (data1,
	    g_marshal_value_peek_string (param_values + 1),
	    g_marshal_value_peek_string (param_values + 2),
	    data2);
}

/* **********************************************************************************++ */

int getbit(char *set, int number)
{
  set += number / 8;
  return (*set & (1 << (number % 8))) != 0;       /* 0 or 1       */
}

void setbit(char *set, int number, int value)
{
  set += number / 8;
  if (value)
    *set |= 1 << (number % 8);              /* set bit      */
  else
    *set &= ~(1 << (number % 8));           /* clear bit    */
}

/* **********************************************************************************++ */

GST_BOILERPLATE (GstTSSplitter, gst_tssplitter, GstElement,
    GST_TYPE_ELEMENT);

static void gst_tssplitter_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec);
static void gst_tssplitter_get_property (GObject * object, guint prop_id,
    GValue * value, GParamSpec * pspec);

static gboolean gst_tssplitter_set_caps (GstPad * pad, GstCaps * caps);
static GstFlowReturn gst_tssplitter_chain (GstPad * pad, GstBuffer * buf);

static void
gst_tssplitter_base_init (gpointer gclass)
{
  static GstElementDetails element_details = {
    "Splitter for MPEG Transport Streams",
    "Freevo/TSSplitter",
    "split transport stream into multiple transport streams",
    "Soenke Schwardt <schwardt@users.sourceforge.net>"
  };
  GstElementClass *element_class = GST_ELEMENT_CLASS (gclass);

  /* FIXME obsolete */
  gst_element_class_add_pad_template (element_class,
				      gst_static_pad_template_get (&src_factory));

  gst_element_class_add_pad_template (element_class,
      gst_static_pad_template_get (&sink_factory));
  gst_element_class_set_details (element_class, &element_details);
}

/* initialize the plugin's class */
static void
gst_tssplitter_class_init (GstTSSplitterClass * klass)
{
  GObjectClass *gobject_class;
  GstElementClass *gstelement_class;

  gobject_class = (GObjectClass *) klass;
  gstelement_class = (GstElementClass *) klass;

  gobject_class->set_property = gst_tssplitter_set_property;
  gobject_class->get_property = gst_tssplitter_get_property;

  g_object_class_install_property (gobject_class, PROP_DEBUG_OUTPUT,
      g_param_spec_boolean ("debug-output", "DebugOutput", "Produce verbose debug output?",
          FALSE, G_PARAM_READWRITE));

  g_object_class_install_property (gobject_class, PROP_SIGNAL_NEW_PIDS,
      g_param_spec_boolean ("signalnewpids", "SignalOnNewPids", "Send signal if new pid is found?",
          FALSE, G_PARAM_READWRITE));

  gst_tssplitter_signals[SIGNAL_SET_FILTER] =
    g_signal_new ("set-filter",                                    /* signal name */
		  G_TYPE_FROM_CLASS (klass),                       /* itype */
		  G_SIGNAL_RUN_LAST,                               /* signal flags */
		  G_STRUCT_OFFSET (GstTSSplitterClass, set_filter),/* class closure */
		  NULL,                                            /* accumulator */
		  NULL,                                            /* accu_data */
		  marshal_VOID__STRING_STRING,                     /* c_marshaller */
		  G_TYPE_NONE,                                     /* return type */
		  2,                                               /* n_params */
		  G_TYPE_STRING,                                   /* param name */
		  G_TYPE_STRING);                                  /* param pids */

  gst_tssplitter_signals[SIGNAL_REMOVE_FILTER] =
    g_signal_new ("remove-filter",                                 /* signal name */
		  G_TYPE_FROM_CLASS (klass),                       /* itype */
		  G_SIGNAL_RUN_LAST,                               /* signal flags */
		  G_STRUCT_OFFSET (GstTSSplitterClass, remove_filter),/* class closure */
		  NULL,                                            /* accumulator */
		  NULL,                                            /* accu_data */
		  g_cclosure_marshal_VOID__STRING,                 /* c_marshaller */
		  G_TYPE_NONE,                                     /* return type */
		  1,                                               /* n_params */
		  G_TYPE_STRING);                                  /* param name */

  klass->set_filter = GST_DEBUG_FUNCPTR (gst_tssplitter_set_filter);
  klass->remove_filter = GST_DEBUG_FUNCPTR (gst_tssplitter_remove_filter);
}

/* initialize the new element
 * instantiate pads and add them to element
 * set functions
 * initialize structure
 */
static void
gst_tssplitter_init (GstTSSplitter * filter,
    GstTSSplitterClass * gclass)
{
  int i;
  GstElementClass *klass = GST_ELEMENT_GET_CLASS (filter);

  filter->sinkpad =
      gst_pad_new_from_template (gst_element_class_get_pad_template (klass, "sink"), "sink");
  gst_pad_set_setcaps_function (filter->sinkpad, gst_tssplitter_set_caps);
  gst_pad_set_getcaps_function (filter->sinkpad, gst_pad_proxy_getcaps);

/*   filter->srcpad = */
/*       gst_pad_new_from_template (gst_element_class_get_pad_template (klass, "src"), "src"); */
/*   gst_pad_set_getcaps_function (filter->srcpad, gst_pad_proxy_getcaps); */

  gst_element_add_pad (GST_ELEMENT (filter), filter->sinkpad);
/*   gst_element_add_pad (GST_ELEMENT (filter), filter->srcpad); */
  gst_pad_set_chain_function (filter->sinkpad, gst_tssplitter_chain);

  /* init internal data */
  filter->debug_output = FALSE;
  filter->signal_new_pids = FALSE;

  /* init filter list */
  filter->filterlist_len = GST_TSSPLITTER_INIT_FILTERLIST_LEN;
  filter->filterlist_free = GST_TSSPLITTER_INIT_FILTERLIST_LEN;
  filter->filterlist = g_malloc( sizeof(GstTSSplitterFilter) * GST_TSSPLITTER_INIT_FILTERLIST_LEN );
  for(i = 0; i < GST_TSSPLITTER_INIT_FILTERLIST_LEN; ++i) {
    filter->filterlist[i].name = NULL;
    filter->filterlist[i].pidlist = NULL;
    filter->filterlist[i].pad = NULL;
  }
  filter->inbuffer = gst_buffer_new();
}

static void
gst_tssplitter_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec)
{
  GstTSSplitter *filter = GST_TSSPLITTER (object);

  switch (prop_id) {
    case PROP_DEBUG_OUTPUT:
      filter->debug_output = g_value_get_boolean (value);
      break;
    case PROP_SIGNAL_NEW_PIDS:
      filter->signal_new_pids = g_value_get_boolean (value);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}

static void
gst_tssplitter_get_property (GObject * object, guint prop_id,
    GValue * value, GParamSpec * pspec)
{
  GstTSSplitter *filter = GST_TSSPLITTER (object);

  switch (prop_id) {
    case PROP_DEBUG_OUTPUT:
      g_value_set_boolean (value, filter->debug_output);
      break;
    case PROP_SIGNAL_NEW_PIDS:
      g_value_set_boolean (value, filter->signal_new_pids);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}

/* GstElement vmethod implementations */

/* this function handles the link with other elements */
static gboolean
gst_tssplitter_set_caps (GstPad * pad, GstCaps * caps)
{
  GstTSSplitter *filter;
  GstPad *otherpad;

  filter = GST_TSSPLITTER (gst_pad_get_parent (pad));
  DEBUGf("chain\n");
  otherpad = (pad == filter->srcpad) ? filter->sinkpad : filter->srcpad;

  return gst_pad_set_caps (pad, caps);
}

/* chain function
 * this function does the actual processing
 */

#define COLOR_RED     "\x1b[0;31m"
#define COLOR_GREEN   "\x1b[0;32m"
#define COLOR_GELB    "\x1b[0;33m"
#define COLOR_BLUE    "\x1b[0;34m"
#define COLOR_PURPLE  "\x1b[0;35m"
#define COLOR_CYAN    "\x1b[0;36m"
#define COLOR_WHITE   "\x1b[0;37m"
#define COLOR_NORMAL  "\x1b[0m"

/*
 * printHexDump()
 * gibt packetlen Zeichen aus dem buffer als HexDump aus
 */
void printHexDump( int packetlen, unsigned char *buffer ) {
  int pos=0;
  // Ausgeben, solange Paketlänge bzw. dumpLength nicht überschritten wird
  while (pos < packetlen) {
    // Anfang einer Zeile? Dann den aktuellen Offset ausgeben
    if (pos%16 == 0) {
      printf(COLOR_RED "%06x: " COLOR_NORMAL , pos);
    }
    // Hexdump von einem Byte ausgeben
    printf("%02x ", buffer[pos]);
    // ein Zeichen im Paket weiterspringen
    pos++;
    // Sind wir am Ende einer Zeile? Wenn ja, dann die lesbaren Zeichen ausgeben
    if (pos%16 == 0) {
      printf("  ");
      int i;
      for(i=16; i > 0; i--) {
	if ((32 <= buffer[pos-i]) &&
	    (buffer[pos-i] <= 127)) {
	  printf("%c", buffer[pos-i]);
	} else {
	  printf(".");
	}
      }
      printf("\n");
    }
  }
  // Die letzte Zeile des HexDumps ist ausgegeben worden.
  // Waren in der letzten Zeile weniger als 16 Zeichen (==> lesbare Zeichen wurden nicht ausgegeben)?
  if (pos%16 != 0) {
    // ja, entsprechend großen Leerraum ausgeben
    printf("  ");
    int i;
    for(i=16-(pos%16); i > 0; i--) {
      printf("   ");
    }
    // die verbliebenen Zeichen ausgeben
    for(i=(pos%16); i > 0; i--) {
      if ((32 <= buffer[pos-i]) &&
	  (buffer[pos-i] <= 127)) {
	printf("%c", buffer[pos-i]);
      } else {
	printf(".");
      }
    }
    printf("\n");
  }
  printf("\n");
}



static gint process_ts_frames(GstTSSplitter *filter, guint8* buffer, int buflen) 
{
  unsigned int i;

  if (buflen < 2*188) {
    DEBUGf("FIXME: got less than 2*188 bytes");
    return buflen;
  }

  // check if they are really transport stream frames
  for ( i = 0; i < 188 ; i++){
    if (( buffer[i] == 0x47 ) &&
	( buffer[i+188] == 0x47 )) {
      break;
    }
  }
  if ( i == 188){
    DEBUGf( "not a transport stream or stream broken");
    return buflen-188;
  } else if (i) {
    DEBUGf( "dropping %d bytes to get TS in sync", i);
    // if unequal 0 then cutoff bogus
    /*     buffer += i; */
    /*     buflen -= i; */
  }

/*   DEBUGf("processing %d bytes", buflen); */

  // iterate through all complete frames
  while( buflen - i >= 188 ) {

    // check frame
    if (buffer[i] != 0x47) {

      // frame invalid
      DEBUGf( "invalid ts frame (i=%d - val=0x%02x)", i, buffer[i] );

      // check if they are really transport stream frames
      while( ((buflen - i) >= 188) && (buffer[i] != 0x47) ) {
	++i;
      }
      DEBUGf( "trying new position (i=%d - val=0x%02x)", i, buffer[i] );
      if ( buffer[i] != 0x47) {
	DEBUGf( "not a transport stream or stream broken (after seek)");
	return 188;
      } 

    } else {

      // frame ok
      int ts_error = ((int)(buffer[i+1] & 0x80) >> 7);
      int  pid      = ((((int)buffer[i+1] & 0x1F) << 8) | ((int)buffer[i+2] & 0xFF));
      int  ts_sc    = ((int)(buffer[i+3] & 0xC0) >> 6);

      // FIXME TODO implement counter to reduce output
      if (ts_error) {
	DEBUGf( "ts frame is damaged i=%d!",i);
      }
      if (ts_sc) {
	DEBUGf( "ts frame is scrambled!");
      }

      GstTSSplitterFilter *filterlist = filter->filterlist;
      int cnt = filter->filterlist_len;
      // iterate over all registered filters
      while (filterlist->name && (cnt > 0)) {
	
	if (getbit(filterlist->pidlist, pid)) {
	  assert(filterlist->name);
	  assert(filterlist->pad);

	  // fill gst buffer
	  GstBuffer *gstbuf = gst_buffer_new_and_alloc(188);
	  gst_buffer_set_data(gstbuf, &buffer[i], 188);

	  // add ts frame to pad
	  gst_pad_push (filterlist->pad, gstbuf);

	  // DEBUGf("Adding ts frame to pad '%s'\n", filterlist->name);
	}
	filterlist++;
      }
    }
    // jump to next ts frame
    i += 188;
  }

  // return remaining bytes
  return (buflen - i);
}


static GstFlowReturn
gst_tssplitter_chain (GstPad * pad, GstBuffer * buf)
{
  GstTSSplitter *filter;
  static int i = 0;

  filter = GST_TSSPLITTER (GST_OBJECT_PARENT (pad));

/*   DEBUGf("bytes from last iteration=%d\n", GST_BUFFER_SIZE(filter->inbuffer)); */
/*   printHexDump( GST_BUFFER_SIZE(filter->inbuffer), filter->inbuffer->data ); */

  GstBuffer *gstbuf = gst_buffer_merge( filter->inbuffer, buf );
/*   DEBUGf("bytes in new buffer=%d\n", GST_BUFFER_SIZE(gstbuf)); */
/*   printHexDump( GST_BUFFER_SIZE(filter->inbuffer) + 64, gstbuf->data ); */
  
  int remaining = process_ts_frames(filter, gstbuf->data, gstbuf->size);
/*   DEBUGf("remaining bytes = %d", remaining); */
/*   printf("\nREMAINING BYTES2:\n"); */
/*   printHexDump( (remaining), &gstbuf->data[ GST_BUFFER_SIZE(gstbuf) - remaining ] ); */

/*   DEBUGf("remaining=%d > buffer=%d", remaining, GST_BUFFER_SIZE(filter->inbuffer)); */
  if (remaining > GST_BUFFER_SIZE(filter->inbuffer)) {
    gst_buffer_unref(filter->inbuffer);
    filter->inbuffer = gst_buffer_new_and_alloc(remaining+20*188);
  }

  GstBuffer *tmpbuf = gst_buffer_create_sub(gstbuf, GST_BUFFER_SIZE(gstbuf) - remaining, remaining);
  gst_buffer_unref(filter->inbuffer);
  filter->inbuffer = gst_buffer_copy(tmpbuf);
  gst_buffer_unref(tmpbuf);

  gst_buffer_unref(gstbuf);

/*   - EIGENEN EINGANGS-BUFFER FÜR MÖGLICHE RESTE ANLEGEN UND DIESE BEIM NÄCHSTEN AUFRUF BEACHTEN */
/*   - Pointer auf Restebuffer an TSFrameSuchFunktion übergeben */
/*   - Pointer auf IncomingBuffer an TSFrameSuchFunktion übergeben */

  /* http://gstreamer.freedesktop.org/data/doc/gstreamer/head/gstreamer-libs/html/GstAdapter.html */

  i += buf->size;
/*   DEBUGf("processing data: bufsize=%d  len=%d", buf->size, i); */

  return GST_FLOW_OK;
  /* just push out the incoming buffer without touching it */
  /*  return gst_pad_push (filter->srcpad, buf); */
}


/* TSFrameSuchFunktion: */
/* - suchen nach TS Frame Preambel */
/* - PID raussuchen */
/* - gesamte Filterlist durchsuchen */
/*   - wenn PID matcht, dann TSFrame an das Pad anhängen */


static GstTSSplitterFilter *gst_tssplitter_find_filter(GstTSSplitter *filter, char *name)
{
  DEBUGf("find filter(%s)", name);
  int i;
  for(i = 0; i < filter->filterlist_len; ++i) {
    if (filter->filterlist[i].name && (!strcasecmp(filter->filterlist[i].name, name))) {
      return &filter->filterlist[i];
    }
  }    
  return NULL;
}

static GstTSSplitterFilter *gst_tssplitter_add_new_filter(GstTSSplitter *filter, char *name)
{
  int i = -1;
   /* request more mempry if needed */
  if (filter->filterlist_free == 0) {
    DEBUGf("no free space (cnt=%d/free=%d) - requesting more memory", 
	   filter->filterlist_len, filter->filterlist_free);

    gint oldsize = filter->filterlist_len;
    filter->filterlist_len += 5;
    filter->filterlist = g_realloc( filter->filterlist, sizeof(GstTSSplitterFilter) * filter->filterlist_len );
    assert(filter->filterlist);
    filter->filterlist_free += 5;
    for(i=oldsize; i<filter->filterlist_len; ++i) {
      filter->filterlist[i].name = NULL;
      filter->filterlist[i].pidlist = NULL;
      filter->filterlist[i].pad = NULL;
    }
  }

  i = filter->filterlist_len - filter->filterlist_free;
  // fill new pidfilter
  DEBUGf("adding new filter %s", name);
  filter->filterlist[i].name = strdup(name);
  filter->filterlist[i].pad = 
    gst_pad_new_from_template (gst_element_class_get_pad_template (GST_ELEMENT_GET_CLASS (filter), "src"), name);
  filter->filterlist[i].pidlist = malloc( sizeof(char) * (1 << 13) + 5 );
  memset( filter->filterlist[i].pidlist, 0, (sizeof(char) * (1 << 13) + 5) );
  
  // add new pad
  gst_element_add_pad (GST_ELEMENT (filter), filter->filterlist[i].pad);

  filter->filterlist_free--;

  return &(filter->filterlist[i]);
}


static void
gst_tssplitter_set_filter(GstTSSplitter *filter, char *name, char* pidlist)
{
  GstTSSplitterFilter *pidfilter = NULL;
  int len=strlen(pidlist);
  int i = 0;
  int pid = 0;
  
  DEBUGf("set_filter(%s)=%s", name, pidlist);

  pidfilter = gst_tssplitter_find_filter(filter, name);
  DEBUGf("find_filter(%s)=%p", name, pidfilter);

  if (!pidfilter) {
    // pidfilter not found ==> add a new one
    pidfilter = gst_tssplitter_add_new_filter(filter, name);
  }
  assert(pidfilter);

  // parse pid list
  while (len > 0) {
    for(i=0; i<len; ++i) {
      if (pidlist[i] == ',') {
	pidlist[i] = '\0';
	pid = atoi(pidlist);

	//	DEBUGf("setfilter: pid=%d", pid);
	setbit(pidfilter->pidlist, pid, 1);

	pidlist += (i+1);
	len -= (i+1);
	break;
      }
    }
    if (i == len) {
      pid = atoi(pidlist);
      //      DEBUGf("setfilter: pid=%d", pid);
      setbit(pidfilter->pidlist, pid, 1);
      break;
    }
  }

  return;
}


static void
gst_tssplitter_remove_filter(GstTSSplitter *filter, char *name)
{
  DEBUGf("remove_filter(%s)", name);

  GstTSSplitterFilter *pidfilter = NULL;
  GstPad *sinkpad = NULL;
  int i = 0;

  // find pidfilter to be removed
  pidfilter = gst_tssplitter_find_filter(filter, name);
  DEBUGf("remove_filter(%s)=%p", name, pidfilter);
  if (!pidfilter)
    return;

  // unlink pad
  sinkpad = gst_pad_get_peer ( pidfilter->pad );
  gst_pad_unlink (pidfilter->pad, sinkpad);

  // remove pad
  gst_element_remove_pad(GST_ELEMENT (filter), pidfilter->pad);
  gst_object_unref(pidfilter->pad);
  pidfilter->pad = NULL;
  
  // free pidlist + name
  free(pidfilter->pidlist);
  pidfilter->pidlist = NULL;
  free(pidfilter->name);
  pidfilter->name = NULL;
  
  // cleanup pidfilterlist
  if (filter->filterlist_len > 1) {
    i = filter->filterlist_len - filter->filterlist_free - 1;
    
    if (filter->filterlist[i].name != NULL) {
      pidfilter->name = filter->filterlist[i].name;
      pidfilter->pidlist = filter->filterlist[i].pidlist;
      pidfilter->pad = filter->filterlist[i].pad;
      
      filter->filterlist[i].name = NULL;
      filter->filterlist[i].pidlist = NULL;
      filter->filterlist[i].pad = NULL;
    } else {
      DEBUGf( "deleting last object in list or something weird is going on" );
    }
  }    
  filter->filterlist_free += 1;
}
