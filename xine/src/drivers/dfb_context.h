/*
 * Copyright (C) 2004-2005 Claudio "KLaN" Ciccani <klan@users.sf.net>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 *
 *  written by Claudio Ciccani <klan82@cheapnet.it> with the contribute
 *  of Kristof Pelckmans <kristof.pelckmans@antwerpen.be>
 *
 *  This file was originally df_xine.h from df_xine in DirectFB-extra and
 *  adapted to kaa.xine by Rob Shortt <rob@tvcentric.com>.
 *
 */

#ifndef __DF_XINE_H__
#define __DF_XINE_H__

#include <sys/types.h>
#include <sys/time.h>
#include <pthread.h>

#include <directfb.h>
#include <directfb_strings.h>
#include <direct/types.h>

#include <xine.h>



typedef void (*DVOutputCallback) ( void                  *cdata,
                                   int                    width,
                                   int                    height,
                                   double                 ratio,
                                   DFBSurfacePixelFormat  format,
                                   DFBRectangle          *dest_rect );

typedef struct {
     IDirectFBSurface *destination;
     IDirectFBSurface *subpicture;

     DVOutputCallback  output_cb;
     void             *output_cdata;

     DVFrameCallback   frame_cb;
     void             *frame_cdata;
} dfb_visual_t;



typedef struct {
     int                          lid;
     int                          layer_level;

     IDirectFBScreen             *screen;        /* output screen */
     IDirectFBDisplayLayer       *layer;         /* output layer */
     DFBDisplayLayerCapabilities  caps;
     DFBDisplayLayerConfig        config;        /* current configuration */
     DFBDisplayLayerBufferMode    buffermode;    /* selected buffermode   */
    
     DFBSurfacePixelFormat        packed_format; /* layer pixelformat used when
                                                    frame format is packed */
     DFBSurfacePixelFormat        planar_format; /* layer pixelformat used when
                                                    frame format is planar */
     DFBSurfacePixelFormat        user_format;   /* selected pixelformat  */
     
     IDirectFBSurface            *surface;
     IDirectFBSurface            *buffer;
     IDirectFBSurface            *subpicture;
     DFBRectangle                 drect;
     DFBSurfaceFlipFlags          flipflags;
     
     IDirectFBDisplayLayer       *underlay;      /* set when the output layer 
                                                    is an overlay */

     pthread_mutex_t              mutex;

     dfb_visual_t                 visual;
     
     struct {
          int                     width;
          int                     height;
          double                  ratio;
          float                   zoom;
          DFBSurfacePixelFormat   format;
     } video;

     int                          fieldparity;
     
     DFBInsets                    crop;
     
     int                          gmode;       /* Visualization/Video */
     
     bool                         update;     
} DFXVideoContext;


typedef struct {
     pthread_t                    thread;
     bool                         active;
     
     IDirectFBEventBuffer        *event;
     xine_event_queue_t          *queue;
     
     DFBColorAdjustment           reset;
     
     int                          pos;
     int                          len;
     int                          status;
     int                          speed;

     bool                         deinterlace;
     int                          field;
     
     int                          default_ratio;
} DFXVideoControl;


typedef struct {
     int                          dst_width;
     int                          dst_height;

     int                          fontsize;

     struct {
          bool                    active;
          xine_osd_t             *img;
          xine_osd_t             *text;
          int                     w;
          int                     h;
     } bar;

     struct {
          bool                    active;
          xine_osd_t             *text;
          int                     w;
          int                     h;
     } info;
     
     bool                         unscaled;
} DFXDisplay;


typedef struct _DFXMrl DFXMrl;

struct _DFXMrl {
     char                        *mrl;

     DFXMrl                      *next;
     DFXMrl                      *prev;
};


typedef struct {
     DFXMrl                      *first;
     DFXMrl                      *last;
     DFXMrl                      *cur;
     int                          repeat;
     int                          repeated;
} DFXMedia;


typedef struct {
     int                           verbosity;
     bool                          scale;
     bool                          hwosd;
     bool                          stdctl;
     char                         *cfg;
     
     int                           xres;
     int                           yres;

     IDirectFB                    *dfb;
     IDirectFBEventBuffer         *input;
     DFBGraphicsDeviceDescription  card_caps;

     xine_t                       *xine;
     xine_video_port_t            *vo;
     xine_audio_port_t            *ao;
     xine_stream_t                *stream;

     xine_post_t                  *post;
     const char                   *post_plugin;

     DFXVideoContext               ctx;

     DFXVideoControl               ctl;

     DFXDisplay                    dpy;

     DFXMedia                      media;
} DFXCore;



typedef struct {
     DFBInputDeviceKeySymbol      key;    /* modifier */
     DFBInputDeviceKeySymbol      subkey;

     short                        event;
     short                        actid;
     short                        param;

     const char                  *help;
     const char                  *stdctl;

} DFXKeyControl;



#define DGM_VIDEO          1
#define DGM_ANIM           2

#define DAN_ACQUIRE        1
#define DAN_RELEASE        2

#define DAI_QUIT           1
#define DAI_TOGGLE_PLAY    2
#define DAI_PLAY           3
#define DAI_TOGGLE_PAUSE   4
#define DAI_SEEK           5
#define DAI_SPEED          6
#define DAI_VOLUME         7
#define DAI_BRIGHTNESS     8
#define DAI_CONTRAST       9
#define DAI_SATURATION    10
#define DAI_HUE           11
#define DAI_RATIO         12
#define DAI_AUDIO_CHANNEL 13
#define DAI_SPU_CHANNEL   14
#define DAI_OSD_HIDE      15
#define DAI_DEINTERLACE   16
#define DAI_ZOOM          17

#define DAP_RESET          0
#define DAP_MINUS         -1
#define DAP_PLUS          +1
#define DAP_RATIO_SQUARE   XINE_VO_ASPECT_SQUARE
#define DAP_RATIO_43       XINE_VO_ASPECT_4_3
#define DAP_RATIO_169      XINE_VO_ASPECT_ANAMORPHIC
#define DAP_RATIO_DVB      XINE_VO_ASPECT_DVB
#define DAP_RATIO_SCREEN   XINE_VO_ASPECT_DVB+1
#define DAP_SEEK_0         0
#define DAP_SEEK_1        10
#define DAP_SEEK_2        20
#define DAP_SEEK_3        30
#define DAP_SEEK_4        40
#define DAP_SEEK_5        50
#define DAP_SEEK_6        60
#define DAP_SEEK_7        70
#define DAP_SEEK_8        80
#define DAP_SEEK_9        90
#define DAP_FIELD_AUTO     0
#define DAP_FIELD_TOP      1
#define DAP_FIELD_BOTTOM   2

#define DDF_BAR            1
#define DDF_INFO           2
#define DDF_BOTH           3



#define DFX_MAGIC( event, notice, action, param ) \
                   ((event << 18) | (notice << 16) | (action << 8) | (param & 0xff))

#define DFX_EVENT( magic )   ((magic >> 18) & 0x3fff)
     
#define DFX_NOTICE( magic )  ((magic >> 16) & 0x0003)

#define DFX_ACTION( magic )  ((magic >>  8) & 0x00ff)

#define DFX_PARAM( magic )   ((char) (magic & 0x00ff))




#define DFBCHECK( x... ) \
{\
     int err = x;\
     if (err != DFB_OK) {\
          fprintf( stderr, "%s <%d>:\n\t", __FILE__, __LINE__ );\
          DirectFBError( #x, err );\
     }\
}

#define SAY( fmt, ... ) \
{\
     if (this->verbosity)\
          fprintf( stderr, "df_xine: " fmt, ## __VA_ARGS__ );\
}

#define ONCE( fmt, ... ) \
{\
     static int once = 1;\
     if (this->verbosity && once) {\
          fprintf( stderr, "df_xine: " fmt, ## __VA_ARGS__ );\
          once = 0;\
     }\
}

#define DBUG( fmt, ... ) \
{\
     if (this->verbosity >= 2 )\
          fprintf( stderr, "df_xine: " fmt, ## __VA_ARGS__ );\
}

#define FATAL( fmt, ... ) \
{\
     fprintf( stderr, "df_xine[!!]: " fmt, ## __VA_ARGS__ );\
}
// dfx_exit( EXIT_FAILURE );

#define DX_ALLOC( size ) \
({\
     register void *__mem;\
     __mem = calloc( 1, (size) );\
     if (!__mem)\
          FATAL( "calloc( 1, %i ) failed at line %i of %s\n",\
               (size), __LINE__, __FILE__ );\
     __mem;\
})

#define DX_STRDUP( str ) \
({\
     register void *__str;\
     __str = strdup( str );\
     if (!__str)\
          FATAL( "strdup( \"%s\" ) failed at line %i of %s\n",\
               str, __LINE__, __FILE__ );\
     __str;\
})

#define DX_TOSTRING( fmt, ... ) \
({\
     char *__str = NULL;\
     if (asprintf( &__str, fmt, ## __VA_ARGS__ ) < 1 || !__str)\
          FATAL( "asprintf( %p, \"%s\", %s ) failed at line %i of %s\n",\
               &__str, fmt, # __VA_ARGS__, __LINE__, __FILE__ );\
     __str;\
})


/* utility functions */

const char*
dfx_format_name( DFBSurfacePixelFormat format );

DFBSurfacePixelFormat
dfx_format_id( const char *name );


/* playlist */

void
dfx_playlist_append( DFXCore *this, const char *mrl );

void
dfx_playlist_discard( DFXCore *this );

void
dfx_playlist_skip( DFXCore *this, int rel );

void
dfx_playlist_free( DFXCore *this );


/* context */

void
dfx_context_create( DFXCore *this );

void
dfx_context_configure( DFXCore *this, int width, int height,
                       DFBSurfacePixelFormat format );

void
dfx_context_set_gmode( DFXCore *this, int mode );

void
dfx_context_release( DFXCore *this );


/* playback control */

void
dfx_control_start( DFXCore *this );

void
dfx_control_dispatch( DFXCore *this, int magic, const struct timeval *tv );

bool
dfx_control_active( DFXCore *this );

void
dfx_control_release( DFXCore *this );


/* osd display */

void
dfx_display_bar( DFXCore *this, const char *text, int pos );

void
dfx_display_text( DFXCore *this, const char *text, ... );

void
dfx_display_status( DFXCore *this, int update );

void
dfx_display_hide( DFXCore *this, int udelay );

void
dfx_display_release( DFXCore *this );


/* core functions */

// Removed so kaa.xine does not have undefined symbol
// void dfx_exit( int status );


/* extras for kaa.xine */

extern void dfx_open_video(DFXCore *this);


#endif /* __DF_XINE_H__ */

