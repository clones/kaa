# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# grid.py - Grid Widget
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

__all__ = [ 'Grid' ]

# python imports
import logging
import copy

# kaa.candy imports imports
import core
from .. import candyxml

# get logging object
log = logging.getLogger('kaa.candy')

class Grid(core.Group):
    """
    Grid Widget
    @note: see C{test/flickr.py} for an example
    @todo: add anaimation support to move inside the grid
    @todo: add parameter to sort items x or y first
    """
    candyxml_name = 'grid'
    context_sensitive = True

    def __init__(self, pos, size, cell_size, cell_item, items, template, context=None):
        """
        Simple grid widget to show the items based on the template.
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param cell_size: (width,height) of each cell
        @param cell_item: string how the cell item should be added to the context
        @param items: list of objects or object name in the context
        @param template: child template for each cell
        @param context: the context the widget is created in
        """
        super(Grid, self).__init__(pos, size, context)
        if isinstance(items, (str, unicode)):
            # items is a string, get it from the context
            self.set_dependency(items)
            items = eval(items, context)
        self.rows = size[0] / cell_size[0]
        self.cols = size[1] / cell_size[1]
        context = copy.copy(context)
        padx = size[0] /self.rows - cell_size[0]
        pady = size[1] /self.cols - cell_size[1]
        x = padx / 2
        y = pady / 2
        for item in items[:self.rows*self.cols]:
            context[cell_item] = item
            child = template(x=x, y=y, size=cell_size, context=context)
            child.set_parent(self)
            x += cell_size[0] + padx
            if x + cell_size[0] > size[0]:
                x = padx / 2
                y += cell_size[1] + pady

    @classmethod
    def candyxml_parse(cls, element):
        """
        Parse the candyxml element for parameter to create the widget. Example::
          <grid width='100' height='100' cell-width='30' cell-height='30'
              cell-item='item' items='listing'>
              <image filename='$item.filename'/>
          </grid>
        There is only one child element allowed, if more is needed you need
        to add a container as child with the real children in it.
        """
        # scale cell-width and cell-height because the auto-scaler does not
        # know about the variables
        cell_width = element.get_scaled('cell-width', 0, int)
        cell_height = element.get_scaled('cell-height', 1, int)
        subelement = element[0]
        # if subelement width or height are the same of the grid it was
        # copied by candyxml from the parent. Set it to cell width or height
        if subelement.width is element.width:
            subelement.width = cell_width
        if subelement.height is element.height:
            subelement.height = cell_height
        # return dict
        return super(Grid, cls).candyxml_parse(element).update(
            template=subelement.xmlcreate(), items=element.items,
            cell_size=(cell_width, cell_height), cell_item=element.cell_item)

# register widget to candyxml
Grid.candyxml_register()
