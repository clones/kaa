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

#define CLUTTER_PARAM_READWRITE \
        G_PARAM_READABLE | G_PARAM_WRITABLE | G_PARAM_STATIC_NAME | G_PARAM_STATIC_NICK |G_PARAM_STATIC_BLURB


/**
 * SECTION:clutter-reflect-texture
 * @short_description: Actor for cloning existing textures in an
 * efficient way.
 *
 * #ClutterReflectTexture allows the cloning of existing #ClutterTexture with
 * a refelction like effect.
 */

#include <GL/gl.h>
#include <clutter/clutter.h>

#if CLUTTER_VERSION_HEX < 0x00070000
#   include <clutter/cogl.h>
#else
#   include <cogl/cogl.h>
#endif
#include "clutter-reflect-texture.h"

enum
{
  PROP_0,
  PROP_REFLECTION_HEIGHT,
  PROP_REFLECT_BOTTOM
};

G_DEFINE_TYPE (ClutterReflectTexture,
	       clutter_reflect_texture,
	       CLUTTER_TYPE_CLONE);

#define CLUTTER_REFLECT_TEXTURE_GET_PRIVATE(obj) \
(G_TYPE_INSTANCE_GET_PRIVATE ((obj), CLUTTER_TYPE_REFLECT_TEXTURE, ClutterReflectTexturePrivate))

struct _ClutterReflectTexturePrivate
{
  gint                 reflection_height, reflect_bottom;
};


static void
clutter_reflect_texture_paint (ClutterActor *actor)
{
  ClutterReflectTexturePrivate *priv;
  ClutterReflectTexture *texture;
  ClutterClone          *clone;
  ClutterTexture        *parent;
  guint                  width, height;
  gfloat                 fwidth, fheight;
  gint                   r_height;
  gint                   opacity;
  gint                   bottom;

  CoglHandle        cogl_texture;
  CoglTextureVertex tvert[4];
  CoglFixed      rty;

  texture = CLUTTER_REFLECT_TEXTURE (actor);
  clone = CLUTTER_CLONE (actor);

  parent = (ClutterTexture*) clutter_clone_get_source (clone);
  if (!parent) 
    return;
  
  if (!CLUTTER_ACTOR_IS_REALIZED (parent))
    clutter_actor_realize (CLUTTER_ACTOR (parent));

  cogl_texture = clutter_texture_get_cogl_texture (parent);
  if (cogl_texture == COGL_INVALID_HANDLE)
    return;

  priv = texture->priv;

  clutter_actor_get_size (CLUTTER_ACTOR(parent), &fwidth, &fheight);
  width = fwidth;
  height = fheight;
      
  if (!height)
      // probably won't happen, but just in case, to avoid divide by zero.
      return;

  r_height = priv->reflection_height;
  bottom = priv->reflect_bottom;
  opacity = clutter_actor_get_opacity(actor);

  if (r_height < 0 || r_height > height)
    r_height = height;

#define FX(x) COGL_FIXED_FROM_INT(x)

  rty = COGL_FIXED_FAST_DIV(FX(bottom ? height-r_height : r_height),FX(height));

  /* clockise vertices and tex coords and colors! */

  tvert[0].x = tvert[0].y = tvert[0].z = 0;
  tvert[0].tx = 0; tvert[0].ty = bottom ? COGL_FIXED_1 : rty;
  tvert[0].color.red = tvert[0].color.green = tvert[0].color.blue = 0xff;
  tvert[0].color.alpha = bottom ? opacity : 0;

  tvert[1].x = FX(width); tvert[1].y = tvert[1].z = 0;
  tvert[1].tx = COGL_FIXED_1; tvert[1].ty = bottom ? COGL_FIXED_1 : rty;
  tvert[1].color.red = tvert[1].color.green = tvert[1].color.blue = 0xff;
  tvert[1].color.alpha = bottom ? opacity : 0;

  tvert[2].x = FX(width); tvert[2].y = FX(r_height); tvert[2].z = 0;
  tvert[2].tx = COGL_FIXED_1; tvert[2].ty = bottom ? rty : 0;
  tvert[2].color.red = tvert[2].color.green = tvert[2].color.blue = 0xff;
  tvert[2].color.alpha = bottom ? 0 : opacity;

  tvert[3].x = 0; tvert[3].y = FX(r_height); tvert[3].z = 0;
  tvert[3].tx = 0; tvert[3].ty = bottom ? rty : 0;
  tvert[3].color.red = tvert[3].color.green = tvert[3].color.blue = 0xff;
  tvert[3].color.alpha = bottom ? 0 : opacity;

  cogl_push_matrix ();

  cogl_set_source_texture(cogl_texture);
  /* FIXME: this does not work as expected */
  /* cogl_polygon(tvert, 4, TRUE); */
  
  cogl_pop_matrix ();
}

static void
clutter_reflect_texture_set_property (GObject      *object,
				    guint         prop_id,
				    const GValue *value,
				    GParamSpec   *pspec)
{
  ClutterReflectTexture         *ctexture = CLUTTER_REFLECT_TEXTURE (object);
  ClutterReflectTexturePrivate  *priv = ctexture->priv;

  switch (prop_id)
    {
    case PROP_REFLECTION_HEIGHT:
      priv->reflection_height = g_value_get_int (value);
      break;
    case PROP_REFLECT_BOTTOM:
      priv->reflect_bottom = g_value_get_boolean(value);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

static void
clutter_reflect_texture_get_property (GObject    *object,
				    guint       prop_id,
				    GValue     *value,
				    GParamSpec *pspec)
{
  ClutterReflectTexture *ctexture = CLUTTER_REFLECT_TEXTURE (object);
  ClutterReflectTexturePrivate  *priv = ctexture->priv;

  switch (prop_id)
    {
    case PROP_REFLECTION_HEIGHT:
      g_value_set_int (value, priv->reflection_height);
      break;
    case PROP_REFLECT_BOTTOM:
      g_value_set_boolean (value, priv->reflect_bottom);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

static void
clutter_reflect_texture_class_init (ClutterReflectTextureClass *klass)
{
  GObjectClass      *gobject_class = G_OBJECT_CLASS (klass);
  ClutterActorClass *actor_class = CLUTTER_ACTOR_CLASS (klass);

  actor_class->paint = clutter_reflect_texture_paint;

  gobject_class->set_property = clutter_reflect_texture_set_property;
  gobject_class->get_property = clutter_reflect_texture_get_property;

  g_object_class_install_property (gobject_class,
                                   PROP_REFLECTION_HEIGHT,
                                   g_param_spec_int ("reflection-height",
                                                     "Reflection Height",
                                                     "",
                                                     0, G_MAXINT,
                                                     0,
                                                     (G_PARAM_CONSTRUCT | CLUTTER_PARAM_READWRITE)));

  g_object_class_install_property (gobject_class,
                                   PROP_REFLECT_BOTTOM,
                                   g_param_spec_boolean("reflect-bottom",
                                                       "Reflection on bottom (TRUE) or top (FALSE) of source",
                                                       "",
                                                       TRUE,
                                                       (G_PARAM_CONSTRUCT | CLUTTER_PARAM_READWRITE)));

  g_type_class_add_private (gobject_class, sizeof (ClutterReflectTexturePrivate));
}

static void
clutter_reflect_texture_init (ClutterReflectTexture *self)
{
  ClutterReflectTexturePrivate *priv;

  self->priv = priv = CLUTTER_REFLECT_TEXTURE_GET_PRIVATE (self);
  priv->reflection_height = 100;
  priv->reflect_bottom = TRUE;
}

/**
 * clutter_reflect_texture_new:
 * @texture: a #ClutterTexture or %NULL
 *
 * Creates an efficient 'reflect' of a pre-existing texture if which it
 * shares the underlying pixbuf data.
 *
 * You can use clutter_reflect_texture_set_parent_texture() to change the
 * parent texture to be reflectd.
 *
 * Return value: the newly created #ClutterReflectTexture
 */
ClutterActor *
clutter_reflect_texture_new (ClutterTexture *texture, gint reflection_height)
{
  g_return_val_if_fail (texture == NULL || CLUTTER_IS_TEXTURE (texture), NULL);

  return g_object_new (CLUTTER_TYPE_REFLECT_TEXTURE,
 		       "source", texture,
		       "reflection-height", reflection_height,
		       "reflect-bottom", TRUE,
		       NULL);
}

