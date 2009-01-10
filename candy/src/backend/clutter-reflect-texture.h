/*
 * ----------------------------------------------------------------------------
 * Clutter Reflection Actor
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa-candy - Third generation Canvas System using Clutter as backend
 * Copyright (C) 2006 OpenedHand / 2008-2009 Dirk Meyer, Jason Tackaberry
 *
 * First Edition: Dirk Meyer <dischi@freevo.org>
 * Maintainer:    Dirk Meyer <dischi@freevo.org>
 *
 * Based on a clutter-tidy actor from Matthew Allum <mallum@openedhand.com>
 * Please see the file AUTHORS for a complete list of authors.
 *
 * This library is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License version
 * 2.1 as published by the Free Software Foundation.
 *
 * This library is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
 * 02110-1301 USA
 *
 * ----------------------------------------------------------------------------
 */

#ifndef _HAVE_CLUTTER_REFLECT_TEXTURE_H
#define _HAVE_CLUTTER_REFLECT_TEXTURE_H

#include <clutter/clutter.h>

G_BEGIN_DECLS

#define CLUTTER_TYPE_REFLECT_TEXTURE (clutter_reflect_texture_get_type ())

#define CLUTTER_REFLECT_TEXTURE(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST ((obj), \
  CLUTTER_TYPE_REFLECT_TEXTURE, ClutterReflectTexture))

#define CLUTTER_REFLECT_TEXTURE_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST ((klass), \
  CLUTTER_TYPE_REFLECT_TEXTURE, ClutterReflectTextureClass))

#define CLUTTER_IS_REFLECT_TEXTURE(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE ((obj), \
  CLUTTER_TYPE_REFLECT_TEXTURE))

#define CLUTTER_IS_REFLECT_TEXTURE_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_TYPE ((klass), \
  CLUTTER_TYPE_REFLECT_TEXTURE))

#define CLUTTER_REFLECT_TEXTURE_GET_CLASS(obj) \
  (G_TYPE_INSTANCE_GET_CLASS ((obj), \
  CLUTTER_TYPE_REFLECT_TEXTURE, ClutterReflectTextureClass))

typedef struct _ClutterReflectTexture        ClutterReflectTexture;
typedef struct _ClutterReflectTexturePrivate ClutterReflectTexturePrivate;
typedef struct _ClutterReflectTextureClass   ClutterReflectTextureClass;

struct _ClutterReflectTexture
{
  ClutterCloneTexture              parent;

  /*< priv >*/
  ClutterReflectTexturePrivate    *priv;
};

struct _ClutterReflectTextureClass
{
  ClutterCloneTextureClass parent_class;

  /* padding for future expansion */
  void (*_clutter_reflect_1) (void);
  void (*_clutter_reflect_2) (void);
  void (*_clutter_reflect_3) (void);
  void (*_clutter_reflect_4) (void);
};

GType           clutter_reflect_texture_get_type           (void) G_GNUC_CONST;

ClutterActor *  clutter_reflect_texture_new                (ClutterTexture      *texture, gint reflection_height);

G_END_DECLS

#endif
