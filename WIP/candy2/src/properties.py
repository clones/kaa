# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# properties.py - Template Property Handling
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008 Dirk Meyer, Jason Tackaberry
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

class Properties(dict):
    """
    Properties class to apply the given properties to a widget.
    """
    candyxml_name = 'properties'

    def apply(self, widget):
        """
        Apply to the given widget.
        """
        for func, value in self.items():
            getattr(widget, 'set_' + func)(*value)
            if func == 'anchor_point':
                widget.move_by(*value)

    @classmethod
    def candyxml_create(cls, element):
        """
        Parse the XML element for parameter and create a Properties object.
        """
        properties = cls()
        for key, value in element.attributes():
            if key in ('opacity', 'depth'):
                value = [ int(value) ]
            elif key in ('scale','anchor_point'):
                value = [ float(x) for x in value.split(',') ]
                if key in ('scale','anchor_point'):
                    value = int(value[0] * element.get_scale_factor()[0]), \
                            int(value[1] * element.get_scale_factor()[1])
            else:
                value = [ value ]
            properties[key] = value
        return properties
