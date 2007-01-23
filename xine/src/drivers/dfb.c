/* -*- coding: iso-8859-1 -*-
 * ----------------------------------------------------------------------------
 * dfb.c - DirectFB Driver
 * ----------------------------------------------------------------------------
 * $Id: $
 *
 * ----------------------------------------------------------------------------
 * Notes:
 *     This file pulls in functions from dfb_context.c and dfb_context.h which 
 *     are from the DirectFB project's DirectFB-extra module and are written 
 *     by Claudio "KLaN" Ciccani <klan@users.sf.net> (df_xine).  Any dfx_
 *     functions in this file are from the same source.  Please see those files
 *     for their copyright information.
 *
 * ----------------------------------------------------------------------------
 * TODO:
 *     Add parameters for selecting:
 *         -which layer to use
 *         -aspect ratio
 *         -deinterlacing
 *         -scaling
 *         -wait for sync
 *
 *     Add the ability to render video to a window's surface, either by
 *     creating a new window or passing a window id.
 *
 * ----------------------------------------------------------------------------
 * kaa-xine - Xine wrapper
 * Copyright (C) 2005 Jason Tackaberry
 *
 * First Edition: Rob Shortt <rob@tvcentric.com>
 * Maintainer:    Rob Shortt <rob@tvcentric.com>
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
 * ------------------------------------------------------------------------- */

#include "dfb.h"
#include "dfb_context.h"

static DFXCore core;

static const DirectFBPixelFormatNames(formats);

const char*
dfx_format_name( DFBSurfacePixelFormat format )
{
     int index = DFB_PIXELFORMAT_INDEX(format);

     if (index > 0 && index < DFB_NUM_PIXELFORMATS)
          return formats[index].name;
     
     return "NONE";
}

DFBSurfacePixelFormat
dfx_format_id( const char *name )
{
     int i;

     for (i = 0; i < sizeof(formats)/sizeof(formats[0]); i++) {
          if (!strcasecmp( name, formats[i].name ))
               return formats[i].format;
     }

     return DSPF_UNKNOWN;
}

void
dfb_driver_dealloc(void *data)
{
    dfb_vo_user_data *user_data = (dfb_vo_user_data *)data;
    free(user_data);
}


int
dfb_get_visual_info(Xine_PyObject *xine, PyObject *kwargs, void **visual_return,
                     driver_info_common **driver_info_return)
{
    int ra_num=4, ra_den=3;
    bool sync = false;
    bool scale = true;

    DFXCore *this = &core;
    memset(this, 0, sizeof( DFXCore ));

    this->verbosity       =  1;
    this->stdctl          = false;
    this->scale           = true;
    this->hwosd           = false;
    this->ctx.lid         = -1;
    this->ctx.layer_level = -1;
    this->ctx.buffermode  = DLBM_BACKVIDEO; // DLBM_FRONTONLY, DLBM_BACKVIDEO, DLBM_TRIPLE
    this->ctx.gmode       = DGM_VIDEO;
    this->media.repeat    =  1;

    // extra
    // this->ctl.deinterlace = 1;
    this->ctx.fieldparity = 1;  // 1 = top, 2 = bottom
    this->ctl.default_ratio = (ra_num << 16) | (ra_den & 0xffff);
    DBUG("default aspect ratio set to %d:%d\n", ra_num, ra_den);

    if(sync) {
        this->ctx.flipflags = DSFLIP_WAITFORSYNC;
        DBUG("will wait for vertical retrace after flipping\n");
    }
    if(!scale) {
        this->scale = false;
        DBUG("video scaling disabled\n");
    }

    DirectFBInit(NULL, NULL);

    DFBCHECK(DirectFBCreate(&this->dfb)); 
    SAY("here we go!\n");
     
    this->dfb->GetDeviceDescription(this->dfb, &this->card_caps);   
 
    pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
    dfx_open_video(this);
    pthread_mutex_init(&mutex, NULL);
    this->ctx.mutex = mutex;     

    dfb_vo_user_data *user_data;

    user_data = malloc(sizeof(dfb_vo_user_data));
    user_data->common.dealloc_cb = dfb_driver_dealloc;

    *visual_return = malloc(sizeof(this->ctx.visual));
    memcpy(*visual_return, &this->ctx.visual, sizeof(this->ctx.visual));
    *driver_info_return = (driver_info_common *)user_data;
    return 1;
}

