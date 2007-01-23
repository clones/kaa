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
 *  This file was originally context.c from df_xine in DirectFB-extra and
 *  adapted to kaa.xine by Rob Shortt <rob@tvcentric.com>.
 *
 */

#ifdef HAVE_CONFIG_H
# include <config.h>
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>

#include "dfb_context.h"



static inline int
dfx_log2( int n )
{
     int i = 0;
     
     while (n >> (i + 1))
          i++;     
     return i;
}


static void
dfx_output_cb( void *data, int width, int height, double ratio,
               DFBSurfacePixelFormat format, DFBRectangle* dest_rect )
{
     DFXCore         *this        = (DFXCore*) data;
     DFXVideoContext *ctx         = &this->ctx;
     bool             update_area = (ctx->video.ratio != ratio);

     if (ctx->update                 ||
         ctx->video.width  != width  ||
         ctx->video.height != height ||
         ctx->video.format != format)
     {
          dfx_context_configure( this, width, height, format );
          update_area = true;
     }

     if (ctx->caps & DLCAPS_SCREEN_LOCATION) {
          if (update_area) {
               int    screen_width;
               int    screen_height;
               double screen_ratio;
               float  x, y, w, h;
               
               ctx->screen->GetSize( ctx->screen, &screen_width, &screen_height );
               screen_ratio = (double)screen_width / (double)screen_height;
               
               if (this->scale) {
                    if (screen_ratio <= ratio) {
                         w = 1.0;
                         h = ((double)screen_width/ratio) / (float)screen_height;
                    }
                    else {
                         w = ((double)screen_height*ratio) / (float)screen_width;
                         h = 1.0;
                    }
               }
               else { /* no scale */
                    w = (float)width / (float)screen_width;
                    h = (float)height / (float)screen_height;
               }
               
               w *= ctx->video.zoom;
               h *= ctx->video.zoom;
               x = (1.0 - w) / 2.0;
               y = (1.0 - h) / 2.0;
                
               ctx->layer->SetScreenLocation( ctx->layer, x, y, w, h );

               ctx->drect.x = 0;
               ctx->drect.y = 0;
               ctx->drect.w = ctx->config.width;
               ctx->drect.h = ctx->config.height;
          }

          *dest_rect = ctx->drect;
          
     } else {
          /* first time we are called or format changed */
          if (update_area) {
               int    screen_width;
               int    screen_height;
               double screen_ratio;
               
               ctx->surface->Clear( ctx->surface, 0, 0, 0, 0xff );
               /* Also clear the surfaces held in the back buffers */
               if (ctx->buffermode != DLBM_FRONTONLY) {
                    ctx->surface->Flip( ctx->surface, NULL, ctx->flipflags );
                    ctx->surface->Clear( ctx->surface, 0, 0, 0, 0xff );
                    
                    if (ctx->buffermode == DLBM_TRIPLE) {
                         ctx->surface->Flip( ctx->surface, NULL, ctx->flipflags );
                         ctx->surface->Clear( ctx->surface, 0, 0, 0, 0xff );
                    }
               }
               
               ctx->screen->GetSize( ctx->screen, &screen_width, &screen_height );
               screen_ratio = (double)screen_width / (double)screen_height;
               
               if (this->scale) {
                    if (screen_ratio <= ratio) {
                         ctx->drect.w = (float) screen_width * 
                                                ctx->video.zoom + .5;
                         ctx->drect.h = (double)screen_width / ratio * 
                                                ctx->video.zoom + .5;
                    } else {
                         ctx->drect.w = (double)screen_height * ratio *
                                                ctx->video.zoom + .5;
                         ctx->drect.h = (float) screen_height *
                                                ctx->video.zoom + .5;
                    }
               }
               else { /* no scale */
                    ctx->drect.w = (float)width  * ctx->video.zoom + .5;
                    ctx->drect.h = (float)height * ctx->video.zoom + .5;
               }                    

               ctx->drect.x = (screen_width  - ctx->drect.w) / 2;
               ctx->drect.y = (screen_height - ctx->drect.h) / 2;
          }

          if (ctx->buffer) {
               /* using hwstretchblit */
               ctx->buffer->GetSize( ctx->buffer, &dest_rect->w, &dest_rect->h );
               dest_rect->x = 0;
               dest_rect->y = 0;
          } else
               *dest_rect = ctx->drect;
     }

     ctx->video.width  = width;
     ctx->video.height = height;
     ctx->video.ratio  = ratio;
     ctx->video.format = format;
     ctx->update       = false;
}

static void
dfx_frame_cb( void *data )
{
     DFXVideoContext  *ctx     = &((DFXCore*) data)->ctx;
     IDirectFBSurface *surface = ctx->surface;
          
     if (ctx->buffer) {
          pthread_mutex_lock( &ctx->mutex ); 
          surface->SetBlittingFlags( surface, DSBLIT_NOFX );
          surface->StretchBlit( surface, ctx->buffer, NULL, &ctx->drect );
          pthread_mutex_unlock( &ctx->mutex );
     }

     surface->Flip( surface, NULL, ctx->flipflags );
}


static void
dfx_test_layer( DFXCore               *this,
                IDirectFBDisplayLayer *layer,
                DFBDisplayLayerConfig *ret_config )
{
     DFXVideoContext       *ctx              = &this->ctx;
     const char            *buffermodes[]    = { "single", "double",
                                                 NULL, "triple", NULL };
     DFBSurfacePixelFormat  packed_formats[] = { DSPF_YUY2, DSPF_UYVY,
                                                 DSPF_RGB16, DSPF_ARGB1555 };
     DFBSurfacePixelFormat  planar_formats[] = { DSPF_YV12, DSPF_I420,
                                                 DSPF_NV12, DSPF_NV21,
                                                 DSPF_NV16 };
     DFBSurfacePixelFormat  format           = DSPF_UNKNOWN;
     DFBDisplayLayerConfig  config;
     
     DFBResult              err;
     int                    i;
 
     /* buffermode test */
     SAY( "-> checking if %s-buffering is supported...",
               buffermodes[dfx_log2( ctx->buffermode )] );
     
     config.flags      = DLCONF_BUFFERMODE;
     config.buffermode = ctx->buffermode;
     err = layer->TestConfiguration( layer, &config, NULL );

     if (this->verbosity)
          fprintf( stderr, (err == DFB_OK) ? "yes\n" : "no" );
     
     if (err == DFB_OK) {
          ret_config->flags      |= DLCONF_BUFFERMODE;
          ret_config->buffermode  = ctx->buffermode;
     }

     /* pixelformat test */
     config.flags = DLCONF_PIXELFORMAT;
     
     if (ctx->user_format) {
          SAY( "-> checking if %s is supported...",
                    dfx_format_name( ctx->user_format ) );
          
          config.pixelformat = ctx->user_format;
          err = layer->TestConfiguration( layer, &config, NULL );
          if (err == DFB_OK) {
               ctx->packed_format = ctx->user_format;
               ctx->planar_format = ctx->user_format;
               format             = ctx->user_format;
          }

          if (this->verbosity)
               fprintf( stderr, (err == DFB_OK) ? "yes\n" : "no\n" );
     }

     if (!format) {
          for (i = 0; i < sizeof(packed_formats)/sizeof(packed_formats[0]); i++) {
               if (ctx->user_format != packed_formats[i]) {
                    SAY( "-> checking if %s is supported...",
                              dfx_format_name( packed_formats[i] ) );

                    config.pixelformat = packed_formats[i];
                    err = layer->TestConfiguration( layer, &config, NULL );
                    
                    if (this->verbosity)
                         fprintf( stderr, (err == DFB_OK) ? "yes\n" : "no\n" );
                    
                    if (err == DFB_OK) { 
                         ctx->packed_format = packed_formats[i];
                         format = packed_formats[i];
                         break;
                    }
               }
          }
                    
          for (i = 0; i < sizeof(planar_formats)/sizeof(planar_formats[0]); i++) {
               if (ctx->user_format != planar_formats[i]) {
                    SAY( "-> checking if %s is supported...",
                              dfx_format_name( planar_formats[i] ) );
                
                    config.pixelformat = planar_formats[i];
                    err = layer->TestConfiguration( layer, &config, NULL ); 
                    
                    if (this->verbosity)
                         fprintf( stderr, (err == DFB_OK) ? "yes\n" : "no\n" );
                    
                    if (err == DFB_OK) {
                         ctx->planar_format = planar_formats[i];
                         format = planar_formats[i];
                         break;
                    }                   
               }
          }
     }
     
     if (format) {
          ret_config->flags       |= DLCONF_PIXELFORMAT;
          ret_config->pixelformat  = format;
     }
}

static DFBEnumerationResult
dfx_scan_layers( DFBDisplayLayerID           id, 
                 DFBDisplayLayerDescription  desc, 
                 void                       *data )
{
     DFXCore               *this   = (DFXCore*) data;
     IDirectFBDisplayLayer *cur    = NULL;
     DFBDisplayLayerConfig  config = { .flags = DLCONF_NONE };
     DFBResult              err;

     if (id == DLID_PRIMARY)
          return DFENUM_OK;
     
     SAY( "probing layer %i\n", id );

     if (!(desc.caps & DLCAPS_SURFACE)) {
          SAY( "-> not usable!\n" );
          return DFENUM_OK;
     } else
          SAY( "-> has a surface\n" );

     if (!(desc.caps & DLCAPS_SCREEN_LOCATION)) {
          SAY( "-> not enough!\n" );
          return DFENUM_OK;
     } else
          SAY( "-> can be positioned on the screen\n" );

     SAY( "-> trying to access..." );

     err = this->dfb->GetDisplayLayer( this->dfb, id, &cur );

     if (err == DFB_OK)
          err = cur->SetCooperativeLevel( cur, DLSCL_EXCLUSIVE );

     if (this->verbosity)
          fprintf( stderr, (err == DFB_OK) ? "ok\n" : "failed\n" );
     
     if (err != DFB_OK) {
          if (cur)
               cur->Release( cur );
          return DFENUM_OK;
     } 

     dfx_test_layer( this, cur, &config );
     this->ctx.lid    = id;
     this->ctx.layer  = cur;
     this->ctx.config = config;

     return DFENUM_CANCEL;
}

static DFBEnumerationResult
dfx_find_underlay( DFBDisplayLayerID           id, 
                   DFBDisplayLayerDescription  desc, 
                   void                       *data )
{
     DFBDisplayLayerID *ret_id = data;
     
     if (desc.caps & DLCAPS_SURFACE) {
          *ret_id = id;
          return DFENUM_CANCEL;
     }
     
     return DFB_OK;
}

extern void
dfx_open_video( DFXCore *this )
{
     DFXVideoContext            *ctx  = &this->ctx;
     DFBDisplayLayerDescription  desc;
     
     if (ctx->lid >= 0) {
          SAY( "forced to use layer %i\n", this->ctx.lid );

          DFBCHECK(this->dfb->GetDisplayLayer( this->dfb,
                                               ctx->lid, &ctx->layer));
          DFBCHECK(ctx->layer->SetCooperativeLevel( ctx->layer,
                                                    DLSCL_EXCLUSIVE ));
          DFBCHECK(ctx->layer->GetScreen( ctx->layer, &ctx->screen ));
          
          dfx_test_layer( this, ctx->layer, &ctx->config );
     } 
     else {
          SAY( "scanning layers for a suitable one\n" );

          DFBCHECK(this->dfb->GetScreen( this->dfb, 
                                         DSCID_PRIMARY, &ctx->screen ));
          ctx->screen->EnumDisplayLayers( ctx->screen,
                                          dfx_scan_layers, (void*)this );

          if (!ctx->layer) {
               SAY( "no suitable layer found\n" );

               ctx->lid = DLID_PRIMARY;
               
               DFBCHECK(this->dfb->GetDisplayLayer( this->dfb,
                                                    DLID_PRIMARY, &ctx->layer ));
               DFBCHECK(ctx->layer->SetCooperativeLevel( ctx->layer, 
                                                         DLSCL_EXCLUSIVE ));
               
               dfx_test_layer( this, ctx->layer, &ctx->config );
          }
     }

     ctx->layer->GetDescription( ctx->layer, &desc );
     ctx->caps = desc.caps;
     if (ctx->lid == DLID_PRIMARY)
          ctx->caps &= ~DLCAPS_SCREEN_LOCATION;
     
     SAY( "using layer %i [%s]\n"
          "\tpacked format: %s\n"
          "\tplanar format: %s\n",
          ctx->lid, desc.name,
          dfx_format_name( ctx->packed_format ),
          dfx_format_name( ctx->planar_format ) );

     if (ctx->caps & DLCAPS_SCREEN_LOCATION) { /* Overlay */
          DFBDisplayLayerID      id = DLID_PRIMARY;
          DFBDisplayLayerConfig  config;
          
          ctx->screen->EnumDisplayLayers( ctx->screen, dfx_find_underlay, &id );
          
          DFBCHECK(this->dfb->GetDisplayLayer( this->dfb, id, &ctx->underlay ));
          ctx->underlay->SetCooperativeLevel( ctx->underlay, DLSCL_EXCLUSIVE );
          ctx->underlay->SetBackgroundMode( ctx->underlay, DLBM_COLOR );
          ctx->underlay->SetBackgroundColor( ctx->underlay, 0, 0, 0, 0 );
          
          if (this->xres && this->yres) {
               config.flags  = DLCONF_WIDTH | DLCONF_HEIGHT;
               config.width  = this->xres;
               config.height = this->yres;
               
               if (ctx->underlay->SetConfiguration( ctx->underlay, &config )) {
                    SAY( "couldn't set video mode to %dx%d\n",
                         config.width, config.height );
               }
          }
          
          /* Check for hardware subpicture */
          if (this->hwosd && desc.caps & DLCAPS_LEVELS) {
               ctx->underlay->GetDescription (ctx->underlay, &desc );
               if (desc.caps & DLCAPS_ALPHACHANNEL) {
                    DFBResult ret;
                    
                    config.flags       = DLCONF_PIXELFORMAT | DLCONF_OPTIONS;
                    config.pixelformat = DSPF_ARGB;
                    config.options     = DLOP_ALPHACHANNEL;
                    
                    ret = ctx->underlay->SetConfiguration( ctx->underlay, &config );
                    if (ret) {
                         config.pixelformat = DSPF_AiRGB;
                         ret = ctx->underlay->SetConfiguration( ctx->underlay, &config );
                    }
                    
                    if (ret == DFB_OK) {
                         ctx->underlay->GetSurface( ctx->underlay, &ctx->subpicture );
                         ctx->layer->SetLevel( ctx->layer, -1 );
                         SAY( "using harwdare OSD.\n" );
                    }
                    else {
                         SAY( "couldn't enable alphachannel.\n" );
                    }
               }
          }
     }
     else { /* Underlay */
          if (this->xres && this->yres) {
               DFBDisplayLayerConfig config;
               
               config.flags  = DLCONF_WIDTH | DLCONF_HEIGHT;
               config.width  = this->xres;
               config.height = this->yres;
               
               if (ctx->layer->SetConfiguration( ctx->layer, &config )) {
                    SAY( "couldn't set video mode to %dx%d\n",
                         config.width, config.height );
               }
          }
     }
     /* force layer to a particular level */
     if (ctx->layer_level > 0) {
          SAY( "forcing layer to level %i\n", this->ctx.layer_level );
          DFBCHECK(ctx->layer->SetLevel( ctx->layer, ctx->layer_level ));
     } 
     
     /* set default options */
     ctx->config.flags |= DLCONF_OPTIONS;
     if (ctx->caps & DLCAPS_FIELD_PARITY && this->ctx.fieldparity)
          ctx->config.options = DLOP_FIELD_PARITY;
     else
          ctx->config.options = DLOP_NONE;

     ctx->layer->SetConfiguration( ctx->layer, &ctx->config );
     ctx->layer->GetConfiguration( ctx->layer, &ctx->config );
     ctx->buffermode = ctx->config.buffermode;
        
     if (ctx->buffermode != DLBM_FRONTONLY)
          ctx->flipflags |= DSFLIP_ONSYNC; /* Matrox BES needs this */
   
     DFBCHECK(ctx->layer->GetSurface( ctx->layer, &ctx->surface ));
     ctx->surface->Clear( ctx->surface, 0, 0, 0, 0xff );
     ctx->surface->Flip( ctx->surface, NULL, DSFLIP_WAITFORSYNC );

     ctx->layer->SetScreenLocation( ctx->layer, 0.0, 0.0, 1.0, 1.0 );
     ctx->layer->SetOpacity( ctx->layer, 0xff );
     if (this->ctx.fieldparity)
          ctx->layer->SetFieldParity( ctx->layer, this->ctx.fieldparity-1 );
          
     /* fill the visual for the video output driver */
     ctx->visual.destination  = ctx->surface;
     ctx->visual.subpicture   = ctx->subpicture;
     ctx->visual.output_cb    = dfx_output_cb;
     ctx->visual.output_cdata = (void*) this;
     ctx->visual.frame_cb     = dfx_frame_cb;
     ctx->visual.frame_cdata  = (void*) this;
     
     ctx->video.zoom = 1.0;
}

/* removing from kaa.xine to shut up warning, it is also not needed 
 *
static void
dfx_open_audio( DFXCore *this )
{
     const char* const *ao_list;
     const char        *ao_driver;

     ao_list = xine_list_audio_output_plugins( this->xine );

     ao_driver = xine_config_register_string( this->xine, "audio.driver",
                                              ao_list[0], "Audio driver to use",
                                              NULL, 0, NULL, NULL );

     this->ao = xine_open_audio_driver( this->xine, ao_driver, NULL );
     
     if (!this->ao)
          FATAL( "couldn't open audio driver '%s'\n", ao_driver );
}
*/


/* not needed for kaa.xine, leaving in and commented out so diffs are easier to read,
 * also shuts up some warnings.
void
dfx_context_create( DFXCore *this )
{
     pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
     
     this->xine = xine_new();
     if (!this->xine)
          FATAL( "failed xine initialization (in xine_new())\n" );

     if (!getenv( "XINERC" )) {
          char *xined;
          xined = DX_TOSTRING( "%s/.xine", getenv( "HOME" ) ? : "~" );
          mkdir( xined, 755 );
          this->cfg = DX_TOSTRING( "%s/config", xined );
          free(xined);
     } else
          this->cfg = DX_STRDUP( getenv( "XINERC" ) );

     if (this->cfg)
          xine_config_load( this->xine, this->cfg );

     xine_init( this->xine );
     xine_engine_set_param( this->xine,
                            XINE_ENGINE_PARAM_VERBOSITY,
                            this->verbosity );

     dfx_open_video( this );
     dfx_open_audio( this );

     this->stream = xine_stream_new( this->xine, this->ao, this->vo );
     if (!this->stream)
          FATAL( "failed stream initialization (in xine_stream_new())\n" );

     xine_set_param( this->stream,
                     XINE_PARAM_VERBOSITY,
                     this->verbosity );
     xine_set_param( this->stream,
                     XINE_PARAM_AUDIO_MUTE,
                     0 );
     xine_set_param( this->stream,
                     XINE_PARAM_AUDIO_CHANNEL_LOGICAL,
                     -1 );
     xine_set_param( this->stream,
                     XINE_PARAM_VO_CROP_TOP,
                     this->ctx.crop.t );
     xine_set_param( this->stream,
                     XINE_PARAM_VO_CROP_BOTTOM,
                     this->ctx.crop.b );
     xine_set_param( this->stream,
                     XINE_PARAM_VO_CROP_LEFT,
                     this->ctx.crop.l );
     xine_set_param( this->stream,
                     XINE_PARAM_VO_CROP_RIGHT,
                     this->ctx.crop.r );

     pthread_mutex_init( &mutex, NULL );
     this->ctx.mutex = mutex;     
}
*/


typedef struct {
     DFXCore *core;
     int      img_area;
     int      width;
     int      height;
} DFXVideoModeData;

static DFBEnumerationResult
dfx_mode_cb( int width, int height, int bpp, void *data )
{
     DFXVideoModeData *mode_data = (DFXVideoModeData*) data;
     DFXCore          *this      = mode_data->core;

     if (mode_data->width  == width &&
         mode_data->height == height)
          return DFENUM_OK;

     SAY( "probing video mode %ix%i...", width, height );

     if (!mode_data->width && !mode_data->height) {
          mode_data->width  = width;
          mode_data->height = height;
          if (this->verbosity)
               fprintf( stderr, "accepted\n" );
     } else
     if (abs( mode_data->img_area - (width * height) ) <
         abs( mode_data->img_area - (mode_data->width * mode_data->height) ))
     {
          mode_data->width  = width;
          mode_data->height = height;
          if (this->verbosity)
               fprintf( stderr, "accepted\n" );
     } else {
          if (this->verbosity)
               fprintf( stderr, "not better\n" );
     }

     return DFENUM_OK;
}

void
dfx_context_configure( DFXCore               *this, 
                       int                    width,
                       int                    height,
                       DFBSurfacePixelFormat  format )
{
     DFXVideoContext       *ctx     = &this->ctx;
     IDirectFB             *dfb     = this->dfb;
     IDirectFBDisplayLayer *layer   = ctx->layer;
     IDirectFBSurface      *surface = ctx->surface;
     DFBDisplayLayerConfig  config;
     
     pthread_mutex_lock( &ctx->mutex );

     DBUG( "updating context\n" );
     
     config.flags = DLCONF_NONE;
     
     switch (format) {
          case DSPF_YUY2:
               if (ctx->packed_format &&
                   ctx->packed_format != ctx->config.pixelformat) {
                    config.flags       |= DLCONF_PIXELFORMAT;
                    config.pixelformat  = ctx->packed_format;
                    DBUG( "changing layer format to %s\n",
                           dfx_format_name( ctx->packed_format ) );
               }
               break;
          case DSPF_YV12:
               if (ctx->planar_format &&
                   ctx->planar_format != ctx->config.pixelformat) {
                    config.flags       |= DLCONF_PIXELFORMAT;
                    config.pixelformat  = ctx->planar_format;
                    DBUG( "changing layer format to %s\n",
                           dfx_format_name( ctx->packed_format ) );
               }
               break;
          default:
               break;
     }

     if (config.flags & DLCONF_PIXELFORMAT) {
          if (ctx->buffer) {
               ctx->buffer->Release( ctx->buffer );
               ctx->buffer = NULL;
          }
     }
     
     if (ctx->caps & DLCAPS_SCREEN_LOCATION) {
          if (ctx->config.width != width) {
               config.flags |= DLCONF_WIDTH;
               config.width  = width;
          }

          if (ctx->config.height != height) {
               config.flags  |= DLCONF_HEIGHT;
               config.height  = height;
          }
     }
     else {
          DFBAccelerationMask accel = this->card_caps.acceleration_mask;
          DFBResult           err;

          if (accel & DFXL_STRETCHBLIT) {
               IDirectFBSurface      *buffer = NULL;
               DFBSurfaceDescription  dsc;

               /* change layer format before testing stretchblit */
               if (config.flags & DLCONF_PIXELFORMAT) {
                    ctx->layer->SetConfiguration( ctx->layer, &config );
                    ctx->layer->GetConfiguration( ctx->layer, &ctx->config );
                    config.flags &= ~DLCONF_PIXELFORMAT;
               }

               if (ctx->buffer) {
                    DFBSurfacePixelFormat f;
                    int                   w, h;
                    
                    ctx->buffer->GetSize( ctx->buffer, &w, &h );
                    ctx->buffer->GetPixelFormat( ctx->buffer, &f );
                    
                    if (w == width && h == height && f == format) {
                         pthread_mutex_unlock( &ctx->mutex );
                         return;
                    }
                         
                    ctx->buffer->Release( ctx->buffer );
                    ctx->buffer = NULL;
               }

               dsc.flags       = DSDESC_WIDTH | DSDESC_HEIGHT |
                                 DSDESC_CAPS  | DSDESC_PIXELFORMAT;
               dsc.caps        = DSCAPS_VIDEOONLY;
               dsc.width       = width;
               dsc.height      = height;
               dsc.pixelformat = format ? : DSPF_YV12;
          
               err = dfb->CreateSurface( dfb, &dsc, &buffer );
          
               if (err == DFB_OK) {
                    /* check if frame format can be scaled/converted to dest surface */
                    surface->GetAccelerationMask( surface, buffer, &accel );

                    if (!(accel & DFXL_STRETCHBLIT)) {
                         if (format != DSPF_YUY2) {
                              buffer->Release( buffer );
                              buffer = NULL;
                             
                              /* generally cards can scale/convert YUY2 */ 
                              dsc.pixelformat = DSPF_YUY2;
                              err = dfb->CreateSurface( dfb, &dsc, &buffer );
                              if (err == DFB_OK)
                                   surface->GetAccelerationMask( surface,
                                                                 buffer, &accel );
                         }
                    
                         if (!(accel & DFXL_STRETCHBLIT)) {
                              if (buffer) {
                                   buffer->Release( buffer );
                                   buffer = NULL;
                              }
                              
                              surface->GetPixelFormat( surface, &dsc.pixelformat );
                              err = dfb->CreateSurface( dfb, &dsc, &buffer );
                              if (err == DFB_OK) {
                                   surface->GetAccelerationMask( surface,
                                                                 buffer, &accel );
                                   
                                   if (!(accel & DFXL_STRETCHBLIT)) {
                                        buffer->Release( buffer );
                                        buffer = NULL;
                                   }
                              }
                         }
                    }
               }
          
               if (buffer) {
                    ONCE( "hwstretchblit detected and enabled\n" );
                    ctx->visual.destination = buffer;
                    ctx->buffer = buffer;
               } else {
                    ONCE( "hwstretchblit test failed, "
                          "forcing video mode selection\n" );
                    ctx->visual.destination = surface;
                    accel &= ~DFXL_STRETCHBLIT;
               }

               xine_port_send_gui_data( this->vo,
                                        XINE_GUI_SEND_SELECT_VISUAL,
                                        (void*) &ctx->visual );
          }
               
          if (!(accel & DFXL_STRETCHBLIT)) {
               DFXVideoModeData data = {
                    .core     = this,
                    .img_area = width * height,
                    .width    = 0,
                    .height   = 0
               };
               int  w, h;
        
               dfb->EnumVideoModes( dfb, dfx_mode_cb, (void*) &data );
               
               ctx->screen->GetSize( ctx->screen, &w, &h );
               if (data.width != w || data.height != h) {
                    SAY( "using video mode to %ix%i\n",
                              data.width, data.height );
                    
                    config.flags  |= DLCONF_WIDTH | DLCONF_HEIGHT;
                    config.width   = data.width;
                    config.height  = data.height;
               } 
               else {
                    SAY( "video mode %ix%i already set\n",
                              data.width, data.height );
               }
          }
     }
    
     if (config.flags != DLCONF_NONE) {
          if (layer->SetConfiguration( layer, &config ))
               SAY( "failed to change layer configuration\n" );
          layer->GetConfiguration( layer, &ctx->config );
     }

     pthread_mutex_unlock( &ctx->mutex );
}

void
dfx_context_set_gmode( DFXCore *this, int mode )
{
     DFXVideoContext *ctx  = &this->ctx;
     xine_post_out_t *audio_source;
     int              has_video;

     if (ctx->gmode == mode)
          return;
     
     if (!this->post_plugin) {
          const char* const *post_list;

          post_list = xine_list_post_plugins_typed( this->xine,
                         XINE_POST_TYPE_AUDIO_VISUALIZATION );
          this->post_plugin = xine_config_register_string( this->xine,
                         "gui.post_audio_plugin", post_list[0],
                         "Audio visualization plugin",
                         NULL, 0, NULL, NULL );
     }

     audio_source = xine_get_audio_source( this->stream );
     has_video    = xine_get_stream_info( this->stream,
                                          XINE_STREAM_INFO_HAS_VIDEO );

     switch (mode) {
          case DGM_VIDEO:
               xine_post_wire_audio_port( audio_source, this->ao );

               if (this->post) {
                    xine_post_dispose( this->xine, this->post );
                    this->post = NULL;
               }

               if (has_video)
                    xine_set_param( this->stream,
                                    XINE_PARAM_IGNORE_VIDEO,
                                    0 );

               DBUG( "graphics mode set to Video\n" );
               break;
               
          case DGM_ANIM:
               if (!this->post) {
                    this->post = xine_post_init( this->xine, this->post_plugin,
                                                 0, &this->ao, &this->vo );
                    if (!this->post) {
                         SAY( "initialization failed for post plugin'%s'\n",
                              this->post_plugin );
                         return;
                    }
               }

               if (has_video)
                    xine_set_param( this->stream,
                                    XINE_PARAM_IGNORE_VIDEO,
                                    1 );

               xine_post_wire_audio_port( audio_source,
                                          this->post->audio_input[0] );

               DBUG( "graphics mode set to Audio Visualization\n" );
               break;

          default:
               DBUG( "unknown graphics mode %i\n", mode );
               return;
     }

     ctx->gmode = mode;
}

void
dfx_context_release( DFXCore *this )
{
     DFXVideoContext *ctx = &this->ctx;

     pthread_mutex_destroy( &ctx->mutex );
     
     if (this->stream)
          xine_dispose( this->stream );

     if (this->post)
          xine_post_dispose( this->xine, this->post );

     if (this->vo)
          xine_close_video_driver( this->xine, this->vo );

     if (this->ao)
          xine_close_audio_driver( this->xine, this->ao );

     if (this->xine) {
          if (this->cfg) {
               xine_config_save( this->xine, this->cfg );
               free( this->cfg );
          }
          
          xine_exit( this->xine );
     }

     if (ctx->buffer)
          ctx->buffer->Release( ctx->buffer );
     
     if (ctx->surface)
          ctx->surface->Release( ctx->surface );

     if (ctx->subpicture)
          ctx->subpicture->Release( ctx->subpicture );
     
     if (ctx->layer) {
          ctx->layer->SetLevel( ctx->layer, 1 );
          ctx->layer->Release( ctx->layer );
     }
          
     if (ctx->underlay)
          ctx->underlay->Release( ctx->underlay );
          
     if (ctx->screen)
          ctx->screen->Release( ctx->screen );
}

