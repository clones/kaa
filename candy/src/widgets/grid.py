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

__all__ = [ 'Grid', 'SelectionGrid' ]

# python imports
import logging
import copy
import time

from kaa.utils import property

# kaa.candy imports imports
import core
from .. import candyxml, animation, is_template, config
from ..behaviour import MAX_ALPHA, Behaviour, create_behaviour

# get logging object
log = logging.getLogger('kaa.candy')

class ScrollBehaviour(Behaviour):
    """
    Behaviour for setting the scrolling steps
    """
    def __init__(self, start, end, func_name):
        super(ScrollBehaviour, self).__init__(start, end)
        self._current = start
        self._func_name = func_name

    def apply(self, alpha_value, widgets):
        """
        Apply behaviour based on alpha value to the widgets
        """
        current = [ int(v) for v in self.get_current(alpha_value) ]
        x = self._current[0] - current[0]
        y = self._current[1] - current[1]
        self._current = current
        for widget in widgets:
            getattr(widget, self._func_name)(x, y)

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
        # store arguments for later private use
        self._orientation = orientation
        self._items = items
        self._cell_item = cell_item
        self._child_template = template
        # do some calculations
        self.num_cols = size[0] / cell_size[0]
        self.num_rows = size[1] / cell_size[1]
        # cell number of the upper left corner if all animations are done
        self._cell0 = [ 0, 0 ]
        # list of rendered items
        self._rendered = {}
        # animations for row and col animation
        self._row_animation = None
        self._col_animation = None
        # padding between cells
        # FIXME: maybe the users wants to set this manually
        padding_x = size[0] /self.num_cols - cell_size[0]
        padding_y = size[1] /self.num_rows - cell_size[1]
        # size of cells
        self._col_size = self.cell_size[0] + padding_x
        self._row_size = self.cell_size[1] + padding_y
        # x0/y0 coordinates for the upper left corner
        # the c* variables will not be changed surung runtime
        self._x0 = self._cx0 = - padding_x / 2
        self._y0 = self._cy0 = - padding_y / 2
        # render visisble items
        self._check_items()

    def scroll_by(self, (rows, cols), secs):
        """
        Scroll by rows and cols cells

        @param rows, cols: rows and cols to scroll
        @param secs: runtime of the animation
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

        @param row, col: end row and col
        @param secs: runtime of the animation
        """
        if self._cell0[0] != row:
            # need to scroll rows
            if self._row_animation and self._row_animation.is_playing:
                self._row_animation.stop()
            start = self._x0 - self._cx0
            self._cell0[0] = row
            stop = self._cell0[0] * self._col_size
            if secs == 0:
                self._scroll(start - stop, 0)
            else:
                b = ScrollBehaviour((start, 0), (stop, 0), '_scroll')
                self._row_animation = self.animate(secs)
                self._row_animation.behave(b)
        if self._cell0[1] != col:
            # need to scroll cols
            if self._col_animation and self._col_animation.is_playing:
                self._col_animation.stop()
            start = self._y0 - self._cy0
            self._cell0[1] = col
            stop = self._cell0[1] * self._row_size
            if secs == 0:
                self._scroll(0, start - stop)
            else:
                b = ScrollBehaviour((0, start), (0, stop), '_scroll')
                self._col_animation = self.animate(secs)
                self._col_animation.behave(b)

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
        child.anchor_point = self.cell_size[0] / 2, self.cell_size[1] / 2
        child.parent = self
        self._rendered[(pos_x, pos_y)] = child
        return child

    def _check_items(self):
        """
        Check for items to add because they are visible now
        """
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

    def _candy_render(self):
        """
        Render the widget
        """
        if 'size' in self._sync_properties:
            log.error('FIXME: kaa.candy.Grid does not support resize')
            return
        super(Grid, self)._candy_render()
        self._obj.set_clip(0, 0, self.width, self.height)

    def _scroll(self, x, y):
        """
        Callback from the animation
        """
        if x:
            self._x0 -= x
            for child in self.children:
                child.x += x
        if y:
            self._y0 -= y
            for child in self.children:
                child.y += y
        self._check_items()
        self._queue_sync(rendering=True)

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
        if element.orientation and element.orientation.lower() == 'vertical':
            orientation = Grid.VERTICAL
        return super(Grid, cls).candyxml_parse(element).update(
            template=subelement.xmlcreate(), items=element.items,
            cell_size=(cell_width, cell_height), cell_item=element.cell_item,
            orientation=orientation)


class SelectionGrid(Grid):
    """
    Grid with selection widget.
    @note: see C{test/flickr.py} for an example
    """

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
        self.behaviour = []
        super(SelectionGrid, self).__init__(pos, size, cell_size, cell_item, items,
            template, orientation, context)
        if is_template(selection):
            selection = selection()
        self.selection = selection
        self.selection.parent = self
        self.selection.lower_bottom()
        self._sel_x = (self.cell_size[0] - self.selection.width) / 2 - self._cx0
        self._sel_y = (self.cell_size[1] - self.selection.height) / 2 - self._cy0
        self._sel_animation = None
        self._sel_modified = []
        self.select((0, 0), 0)

    def behave(self, behaviour, *args, **kwargs):
        """
        Add behaviour to be used for widgets covered by the selection

        @param behaviour: Behaviour object or name registered to the behaviour
           submodule. If a new is given, the Behaviour will be created with
           the given arguments.
        """
        if isinstance(behaviour, str):
            behaviour = create_behaviour(behaviour, *args, **kwargs)
        self.behaviour.append(behaviour)
        for child in self.children:
            if child != self.selection:
                behaviour.apply(0, [child])
        # scroll by 0,0 to update covered items
        self._scroll_listing(0,0)
        return self

    def select(self, (col, row), secs):
        """
        Select a cell.

        @param col, row: cell position to select
        @param secs: runtime of the animation
        """
        dest_x = self._sel_x + col * self._col_size + self._cx0 - self._x0
        dest_y = self._sel_y + row * self._row_size + self._cy0 - self._y0
        if self._sel_animation and self._sel_animation.is_playing:
            self._sel_animation.stop()
        if secs:
            src = (self.selection.x, self.selection.y)
            b = ScrollBehaviour(src, (dest_x, dest_y), '_scroll_listing')
            self._sel_animation = self.animate(secs)
            self._sel_animation.behave(b)
        else:
            self._scroll_listing(self.selection.x - dest_x, self.selection.y - dest_y)

    def _create_item(self, item_num, pos_x, pos_y):
        """
        Render one child
        """
        child = super(SelectionGrid, self)._create_item(item_num, pos_x, pos_y)
        if child:
            for behaviour in self.behaviour:
                behaviour.apply(0, [child])
        return child

    def _scroll_listing(self, x, y):
        """
        Scroll the listing
        """
        self.selection.x -= x
        self.selection.y -= y
        if not self.behaviour:
            # no behaviour means no items to change
            return
        x, y, width, height = self.selection.geometry
        # current cell position of the selection bar
        # get the items that could be affected by a behaviour and check
        # if they are covered by the selection widget
        base_x = (x + self._x0) / self._col_size
        base_y = (y + self._y0) / self._row_size
        in_area = []
        for x0 in range(-1, 2):
            for y0 in range(-1, 2):
                child = self._rendered.get((base_x + x0, base_y + y0))
                if child is None:
                    # not rendered
                    continue
                px = abs(child.x - x)
                py = abs(child.y - y)
                if px > width or py > height:
                    # not covered
                    continue
                coverage = (100 - 100 * px / width) * (100 - 100 * py / height)
                if coverage:
                    # x and y percent coverage
                    in_area.append((coverage, child))
        # sort by coverage and draw from the lowest
        in_area.sort(lambda x,y: cmp(x[0], y[0]))
        modified = self._sel_modified
        self._sel_modified = []
        for coverage, child in in_area:
            child.raise_top()
            for behaviour in self.behaviour:
                behaviour.apply(float(coverage) / 10000 * MAX_ALPHA, [child])
            if child in modified:
                modified.remove(child)
            self._sel_modified.append(child)
        # reset children covered before and not anymore
        for behaviour in self.behaviour:
            behaviour.apply(0, modified)

    @classmethod
    def candyxml_parse(cls, element):
        selection = None
        for child in element:
            if child.node == 'selection':
                selection = child[0].xmlcreate()
                element.remove(child)
        return super(SelectionGrid, cls).candyxml_parse(element).update(
            selection=selection)


# register widgets to candyxml
Grid.candyxml_register()
SelectionGrid.candyxml_register()
