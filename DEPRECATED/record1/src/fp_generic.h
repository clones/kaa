/* File: fp_generic.h
 *
 * Author: Sönke Schwardt <schwardt@users.sourceforge.net>
 *
 * $Id$
 *
 * Copyright (C) 2005 Sönke Schwardt <schwardt@users.sourceforge.net>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 */

#ifndef __FP_GENERIC_H_
#define __FP_GENERIC_H_

#include <string>
#include <vector>

class FilterPlugin {
  public:
  virtual ~FilterPlugin() { };

  /* 
     add data to Filter Plugin buffer
     NOTE: do not process data! may be called often with small chunks
  */
  virtual void add_data( const std::string &data ) = 0;

  /* 
     process data that is within Filter Plugin buffer
  */
  virtual void process_data() = 0;

  /*
    get processed data
  */
  virtual std::string get_data() = 0;  
};

#endif
