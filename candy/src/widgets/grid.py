# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# grid.py - Grid Widget
# -----------------------------------------------------------------------------
# $Id$
#
# Note: scrolling is not as smooth as it should be. The main reason for this
# in the flickr test case is that it uses reflections on the images and the
# reflections are rendered in software in the clutter thread. We may also want
# to load images async in this case:
# http://www.mail-archive.com/pygtk@daa.com.au/msg15323.html
#
# Maybe we also want to remove images we do not see anymore to free some
# memory and in case they are still downloading the image, we want to abort
# that to free bandwidth for images we see right now
#
# -----------------------------------------------------------------------------
# kaa-candy - Third generation Canvas System using Clutter as backend
# Copyright (C) 2008 Dirk Meyer, Jason Tackaberry
#
# First Version: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
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
import time

# kaa.candy imports imports
import core
from .. import candyxml, animation, is_template, config

# get logging object
log = logging.getLogger('kaa.candy')

class ScrollAnimation(animation.Animation):

    def __init__ (self, widget, start, stop, secs, orientation):
        super(ScrollAnimation, self).__init__(secs, animation.alpha_inc_func)
        self._start = start
        self._diff = stop - start
        self._current = start
        self._orientation = orientation
        self.apply(widget)
        self.start()

    def stop(self):
        """
        Stop the animation and return missing steps
        """
        super(ScrollAnimation, self).stop()
        return self._diff - (self._current - self._start)

    def _candy_animate(self, alpha_value):
        """
        Callback with the new alpha value
        """
        alpha = float(alpha_value) / animation.MAX_ALPHA
        current = self._start + int(self._diff * alpha)
        step = self._current - current
        self._current = current
        for actor in self.widgets:
            actor._scroll(step, self._orientation)

class Grid(core.Group):
    """
    Grid Widget
    @note: see C{test/flickr.py} for an example
    """
    candyxml_name = 'grid'
    context_sensitive = True

    HORIZONTAL, VERTICAL =  range(2)

    def __init__(self, pos, size, cell_size, cell_item, items, template,
                 orientation, context=None):
        """
        Simple grid widget to show the items based on the template.
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget.
        @param cell_size: (width,height) of each cell
        @param cell_item: string how the cell item should be added to the context
        @param items: list of objects or object name in the context
        @param template: child template for each cell
        @param orientation: how to arange the grid: Grid.HORIZONTAL or Grid.VERTICAL
        @param context: the context the widget is created in
        """
        super(Grid, self).__init__(pos, size, context)
        # clip the grid to hide cells moved outside the visible area
        if isinstance(items, (str, unicode)):
            # items is a string, get it from the context
            items = self.eval_context(items)
        # store arguments for later public use
        self.cell_size = cell_size
        # do some calculations
        self.num_cols = size[0] / cell_size[0]
        self.num_rows = size[1] / cell_size[1]
        # padding between cells
        padding_x = size[0] /self.num_cols - cell_size[0]
        padding_y = size[1] /self.num_rows - cell_size[1]
        # size of cells
        self._col_size = self.cell_size[0] + padding_x
        self._row_size = self.cell_size[1] + padding_y
        # x0/y0 coordinates for the upper left corner and cell visible
        # there if all animations would be done
        self._x0 = - padding_x / 2
        self._y0 = - padding_y / 2
        self._cell0 = [ 0, 0 ]
        # list of rendered items
        self._rendered = {}
        # animations for row and col animation
        self._row_animation = None
        self._col_animation = None
        # store arguments for later private use
        self._orientation = orientation
        self._items = items
        self._cell_item = cell_item
        self._child_template = template
        self._check_items()

    def destroy(self):
        """
        Destroy the widget by stopping running animations.
        """
        if self._row_animation and self._row_animation.is_playing():
            self._row_animation.stop()
        self._row_animation = None
        if self._col_animation and self._col_animation.is_playing():
            self._col_animation.stop()
        self._col_animation = None
        super(Grid, self).destroy()

    def scroll_by(self, (rows, cols), secs):
        """
        Scroll by rows and cols cells
        """
        while True:
            # check if it possible to go there
            if self._orientation == Grid.HORIZONTAL:
                num = (self._cell0[0] + rows) * self.num_rows + (self._cell0[1] + cols)
            if self._orientation == Grid.VERTICAL:
                num = (self._cell0[1] + cols) * self.num_cols + (self._cell0[0] + rows)
            if num >= 0 and num < len(self._items):
                # there is an item in the upper left corner
                break
            # remove one cell in scroll, start with rows and use cols if
            # there are no rows to scroll anymore
            if rows:
                rows -= (rows / abs(rows))
            else:
                cols -= (cols / abs(cols))
        self.scroll_to((self._cell0[0] + rows, self._cell0[1] + cols), secs)

    def scroll_to(self, (row, col), secs):
        """
        Scroll to row / cell position
        """
        if self._cell0[0] != row:
            # need to scroll rows
            start = self._cell0[0] * self._col_size
            if self._row_animation and self._row_animation.is_playing():
                start -= self._row_animation.stop()
            self._cell0[0] = row
            stop = self._cell0[0] * self._col_size
            if secs == 0:
                self._scroll(start - stop, 0)
            else:
                self._row_animation = ScrollAnimation(self, start, stop, secs, 0)
        if self._cell0[1] != col:
            # need to scroll cols
            start = self._cell0[1] * self._row_size
            if self._col_animation and self._col_animation.is_playing():
                start -= self._col_animation.stop()
            self._cell0[1] = col
            stop = self._cell0[1] * self._row_size
            if secs == 0:
                self._scroll(start - stop, 1)
            else:
                self._col_animation = ScrollAnimation(self, start, stop, secs, 1)

    def _create_item(self, item_num, pos_x, pos_y):
        """
        Render one child
        """
        if item_num < 0 or item_num >= len(self._items):
            self._rendered[(pos_x, pos_y)] = None
            return
        x = pos_x * self._col_size -self._x0
        y = pos_y * self._row_size -self._y0
        if x >= self.width or y >= self.height:
            # refuse to draw invisible items
            return
        context = copy.copy(self.get_context())
        context[self._cell_item] = self._items[item_num]
        child = self._child_template(context=context)
        child.x = x
        child.y = y
        child.width, child.height = self.cell_size
        child.parent = self
        self._rendered[(pos_x, pos_y)] = child
        return child

    def _check_items(self):
        # This function is highly optimized for fast rendering when there is nothing
        # to change. Some code is duplicated for HORIZONTAL and VERTICAL but creating
        # smaller code size increases the running time.

        # current item left/top position in the grid
        base_x = self._x0 / self._col_size
        base_y = self._y0 / self._row_size
        pos_x = base_x
        pos_y = base_y
        if self._orientation == Grid.HORIZONTAL:
            item_num = base_x * self.num_rows + base_y
            while True:
                if not (pos_x, pos_y) in self._rendered:
                    self._create_item(item_num, pos_x, pos_y)
                item_num += 1
                pos_y += 1
                if pos_y - base_y >= self.num_rows:
                    if not (pos_x, pos_y) in self._rendered:
                        self._create_item(item_num, pos_x, pos_y)
                    pos_y = base_y
                    pos_x += 1
                    if pos_x - base_x > self.num_cols:
                        return

        # self._orientation == Grid.VERTICAL
        item_num = base_y * self.num_cols + base_x
        while True:
            if not (pos_x, pos_y) in self._rendered:
                self._create_item(item_num, pos_x, pos_y)
            item_num += 1
            pos_x += 1
            if pos_x - base_x >= self.num_cols:
                if not (pos_x, pos_y) in self._rendered:
                    self._create_item(item_num, pos_x, pos_y)
                pos_x = base_x
                pos_y += 1
                if pos_y - base_y > self.num_rows:
                    return
        return

    def _candy_layout(self):
        """
        Layout the widget
        """
        super(Grid, self)._candy_layout()
        self._obj.set_clip(0, 0, self.width, self.height)

    def _scroll(self, step, orientation):
        """
        Callback from the animation
        """
        # move children
        if orientation == Grid.HORIZONTAL:
            self._x0 -= step
            for child in self.children:
                child.x += step
        if orientation == Grid.VERTICAL:
            self._y0 -= step
            for child in self.children:
                child.y += step
        self._check_items()
        self._require_update(rendering=True)

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
        orientation = Grid.HORIZONTAL
        if element.orientation and element.orientation.lower() in 'vertical':
            orientation = Grid.VERTICAL
        return super(Grid, cls).candyxml_parse(element).update(
            template=subelement.xmlcreate(), items=element.items,
            cell_size=(cell_width, cell_height), cell_item=element.cell_item,
            orientation=orientation)


class SelectionGrid(Grid):

    candyxml_style = 'selection'

    def __init__(self, pos, size, cell_size, cell_item, items, template,
                 selection, orientation, context=None):
        """
        Simple grid widget to show the items based on the template.
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget.
        @param cell_size: (width,height) of each cell
        @param cell_item: string how the cell item should be added to the context
        @param items: list of objects or object name in the context
        @param template: child template for each cell
        @param selection: widget for the selection
        @param orientation: how to arange the grid: Grid.HORIZONTAL or Grid.VERTICAL
        @param context: the context the widget is created in
        """
        super(SelectionGrid, self).__init__(pos, size, cell_size, cell_item, items,
            template, orientation, context)
        if is_template(selection):
            selection = selection()
        if selection:
            self.add(selection)

    @classmethod
    def candyxml_parse(cls, element):
        selection = None
        return super(SelectionGrid, cls).candyxml_parse(element).update(
            selection=selection)


# register widgets to candyxml
Grid.candyxml_register()
SelectionGrid.candyxml_register()
