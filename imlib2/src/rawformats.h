/*
 * ----------------------------------------------------------------------------
 * Imlib2 wrapper for Python
 * ----------------------------------------------------------------------------
 * $Id$
 *
 * ----------------------------------------------------------------------------
 * kaa.imlib2 - An imlib2 wrapper for Python
 * Copyright (C) 2004-2006 Jason Tackaberry <tack@urandom.ca>
 *
 * First Edition: Jason Tackaberry <tack@urandom.ca>
 * Maintainer:    Jason Tackaberry <tack@urandom.ca>
 *
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

unsigned int get_raw_bytes_size(char *format);
unsigned char *get_raw_bytes(char *format, unsigned char *dstbuf);
unsigned char *convert_raw_rgba_bytes(char *from_format, char *to_format,
                                      unsigned char *from_buf, unsigned char *to_buf,
                                      int w, int h);
