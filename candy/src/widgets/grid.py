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

# kaa imports
import kaa
from kaa.utils import property

# kaa.candy imports imports
from container import Group
from .. import candyxml, animation, is_template, config
from ..behaviour import MAX_ALPHA, Behaviour, create_behaviour

# get logging object
log = logging.getLogger('kaa.candy')

class ScrollBehaviour(Behaviour):
    """
    Behaviour for setting the scrolling steps
    """
    def __init__(self, (x, y), func_name):
        super(ScrollBehaviour, self).__init__((0,0), (x,y))
        self._current = (0,0)
        self._func_name = func_name

    def apply(self, alpha_value, widgets):
        """
        Apply behaviour based on alpha value to the widgets
        """
        current = [ int(v) for v in self.get_current(alpha_value) ]
        x = current[0] - self._current[0]
        y = current[1] - self._current[1]
        self._current = current
        for widget in widgets:
            getattr(widget, self._func_name)(x, y)


class ItemGroup(Group):
    def __init__(self, pos):
        super(ItemGroup, self).__init__(pos)
        # x,y coordinates of the items group in the grid. These will never
        # change will will be kep as reference
        self.x0, self.y0 = pos
        # cell number of the upper left corner if all animations are done
        self.cell0 = [ 0, 0 ]


class Grid(Group):
    """
    Grid Widget
    @note: see C{test/flickr.py} for an example
    """
    candyxml_name = 'grid'
    context_sensitive = True

    HORIZONTAL, VERTICAL =  range(2)

    def __init__(self, pos, size, cell_size, cell_item, items, template,
                 orientation, spacing=None, context=None):
        """
        Simple grid widget to show the items based on the template.

        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget.
        @param cell_size: (width,height) of each cell
        @param cell_item: string how the cell item should be added to the context
        @param items: list of objects or object name in the context
        @param template: child template for each cell
        @param orientation: how to arange the grid: Grid.HORIZONTAL or Grid.VERTICAL
        @param spacing: x,y values of space between two items. If set to None
            the spacing will be calculated based on cell size and widget size
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
        self.__orientation = orientation
        self.__child_listing = items
        self.__child_context = cell_item
        self.__child_template = template
        self.spacing = spacing

    def _create_grid(self):
        """
        Setup the grid. After this function has has been called no modifications
        to the grid are possible.

        @todo: make it possible to change the layout during runtime
        """
        # do some calculations
        if self.spacing is None:
            # no spacing is given. Get the number of rows and cols
            # and device the remaining space as speacing and border
            self.num_cols = self.width / self.cell_size[0]
            self.num_rows = self.height / self.cell_size[1]
            space_x = self.width / self.num_cols - self.cell_size[0]
            space_y = self.height / self.num_rows - self.cell_size[1]
            # size of cells
            self._col_size = self.cell_size[0] + space_x
            self._row_size = self.cell_size[1] + space_y
        else:
            # spacing is given, let's see how much we can fit into here
            space_x, space_y = self.spacing
            # size of cells
            self._col_size = self.cell_size[0] + space_x
            self._row_size = self.cell_size[1] + space_y
            # now that we know the sizes check how much items fit
            self.num_cols = self.width / self._col_size
            self.num_rows = self.height / self._row_size
        # we now center the grid by default
        x0 = (self.width - self.num_cols * self._col_size + space_x) / 2
        y0 = (self.height - self.num_rows * self._row_size + space_y) / 2
        # list of rendered items
        self._rendered = {}
        # animations for row and col scrolling
        self.__row_animation = None
        self.__col_animation = None
        # group of items
        self.items = ItemGroup((x0, y0))
        self.items.parent = self

    def __getattr__(self, attr):
        """
        Generic getattr function called when variables created by grid
        creation are needed.
        """
        if self._create_grid is not None:
            self._create_grid()
            self._create_grid = None
            # call again, now the attribute should be there
            return getattr(self, attr)
        # we do not know that attribute
        raise AttributeError("'Grid' object has no attribute '%s'" % attr)

    @kaa.synchronized()
    def scroll_by(self, (rows, cols), secs, force=False):
        """
        Scroll by rows and cols cells

        @param rows, cols: rows and cols to scroll
        @param secs: runtime of the animation
        """
        # This function will force grid creation
        while not force:
            # check if it possible to go there
            if self.__orientation == Grid.HORIZONTAL:
                num = (self.items.cell0[0] + rows) * self.num_rows + \
                      (self.items.cell0[1] + cols)
            if self.__orientation == Grid.VERTICAL:
                num = (self.items.cell0[1] + cols) * self.num_cols + \
                      (self.items.cell0[0] + rows)
            if num >= 0 and num < len(self.__child_listing):
                # there is an item in the upper left corner
                break
            # remove one cell in scroll, start with rows and use cols if
            # there are no rows to scroll anymore
            if rows:
                rows -= (rows / abs(rows))
            else:
                cols -= (cols / abs(cols))
        self.scroll_to((self.items.cell0[0] + rows, self.items.cell0[1] + cols), secs)

    @kaa.synchronized()
    def scroll_to(self, (row, col), secs):
        """
        Scroll to row / cell position

        @param row, col: end row and col
        @param secs: runtime of the animation
        """
        # This function will force grid creation
        if self.items.cell0[0] != row:
            # need to scroll rows
            if self.__row_animation and self.__row_animation.is_playing:
                self.__row_animation.stop()
            self.items.cell0[0] = row
            x = self.items.cell0[0] * self._col_size + self.items.x - self.items.x0
            if secs == 0:
                self._scroll_grid(x, 0)
            else:
                self.__row_animation = self.animate(secs)
                self.__row_animation.behave(ScrollBehaviour((x, 0), '_scroll_grid'))
        if self.items.cell0[1] != col:
            # need to scroll cols
            if self.__col_animation and self.__col_animation.is_playing:
                self.__col_animation.stop()
            self.items.cell0[1] = col
            y = self.items.cell0[1] * self._row_size + self.items.y - self.items.y0
            if secs == 0:
                self._scroll_grid(0, y)
            else:
                self.__col_animation = self.animate(secs)
                self.__col_animation.behave(ScrollBehaviour((0, y), '_scroll_grid'))

    @kaa.synchronized()
    def _scroll_grid(self, x, y):
        """
        Callback from the animation
        """
        self.items.x -= x
        self.items.y -= y
        self._queue_rendering()
        self._queue_sync_properties('grid')

    def _candy_create_item(self, item_num, pos_x, pos_y):
        """
        Render one child
        """
        if item_num < 0 or item_num >= len(self.__child_listing):
            self._rendered[(pos_x, pos_y)] = None
            return
        context = copy.copy(self.get_context())
        context[self.__child_context] = self.__child_listing[item_num]
        child = self.__child_template(context=context)
        child.x = pos_x * self._col_size
        child.y = pos_y * self._row_size
        child.width, child.height = self.cell_size
        child.anchor_point = self.cell_size[0] / 2, self.cell_size[1] / 2
        child.parent = self.items
        self._rendered[(pos_x, pos_y)] = child
        return child

    def _prepare_sync(self):
        """
        Check for items to add because they are visible now
        """
        if self._obj and not 'grid' in self._sync_properties:
            return

        # This function is highly optimized for fast rendering when there is nothing
        # to change. Some code is duplicated for HORIZONTAL and VERTICAL but creating
        # smaller code size increases the running time.

        # current item left/top position in the grid
        base_x = -self.items.x / self._col_size
        base_y = -self.items.y / self._row_size
        pos_x = base_x
        pos_y = base_y
        if self.__orientation == Grid.HORIZONTAL:
            item_num = base_x * self.num_rows + base_y
            while True:
                if not (pos_x, pos_y) in self._rendered:
                    self._candy_create_item(item_num, pos_x, pos_y)
                item_num += 1
                pos_y += 1
                if pos_y - base_y >= self.num_rows:
                    if not (pos_x, pos_y) in self._rendered:
                        self._candy_create_item(item_num, pos_x, pos_y)
                    pos_y = base_y
                    pos_x += 1
                    if pos_x - base_x > self.num_cols:
                        break

        if self.__orientation == Grid.VERTICAL:
            item_num = base_y * self.num_cols + base_x
            while True:
                if not (pos_x, pos_y) in self._rendered:
                    self._candy_create_item(item_num, pos_x, pos_y)
                item_num += 1
                pos_x += 1
                if pos_x - base_x >= self.num_cols:
                    if not (pos_x, pos_y) in self._rendered:
                        self._candy_create_item(item_num, pos_x, pos_y)
                    pos_x = base_x
                    pos_y += 1
                    if pos_y - base_y > self.num_rows:
                        break
        for x, y in self._rendered.keys()[:]:
            if x < base_x - self.num_cols or y < base_y - self.num_rows or \
               x > base_x + 2 * self.num_cols or y > base_y + 2 * self.num_rows:
                child = self._rendered.pop((x,y))
                if child:
                    child.parent = None
        return

    def _candy_render(self):
        """
        Render the widget
        """
        if 'size' in self._sync_properties:
            log.error('FIXME: kaa.candy.Grid does not support resize')
            return
        super(Grid, self)._candy_render()
        self._obj.set_clip(0, 0, self.inner_width, self.inner_height)

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
                 selection, orientation, spacing=None, context=None):
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
        @param spacing: x,y values of space between two items. If set to None
            the spacing will be calculated based on cell size and widget size
        @param context: the context the widget is created in

        """
        self.behaviour = []
        super(SelectionGrid, self).__init__(pos, size, cell_size, cell_item, items,
            template, orientation, spacing, context)
        if is_template(selection):
            selection = selection()
        self.selection = selection
        self.selection.parent = self
        self.selection.lower_bottom()
        self.__animation = None

    def _create_grid(self):
        """
        Setup the grid. After this function has has been called no modifications
        to the grid are possible.

        @todo: make it possible to change the layout during runtime
        """
        super(SelectionGrid, self)._create_grid()
        self.items.modified = []
        self.select((0, 0), 0)

    def behave(self, behaviour, *args, **kwargs):
        """
        Add behaviour to be used for widgets covered by the selection

        @param behaviour: Behaviour object or name registered to the behaviour
           submodule. If a new is given, the Behaviour will be created with
           the given arguments.
        """
        # This function will force grid creation
        if isinstance(behaviour, str):
            behaviour = create_behaviour(behaviour, *args, **kwargs)
        self.behaviour.append(behaviour)
        behaviour.apply(0, self.items.children)
        self._queue_rendering()
        self._queue_sync_properties('selection')
        return self

    def select(self, (col, row), secs):
        """
        Select a cell.

        @param col, row: cell position to select
        @param secs: runtime of the animation
        """
        # This function will force grid creation

        # calculate x,y coordinates to move based on the current position
        # This is the selection x0 if it would be on 0,0 + the row or col
        # we want to select - our current position. After that add how items
        # has scrolled. Sounds complicated but is correct.
        x = (self.cell_size[0] - self.selection.width) / 2 + \
            col * self._col_size - self.selection.x + self.items.x
        y = (self.cell_size[1] - self.selection.height) / 2 + \
            row * self._row_size - self.selection.y + self.items.y
        if self.__animation and self.__animation.is_playing:
            self.__animation.stop()
        if secs:
            self.__animation = self.animate(secs)
            self.__animation.behave(ScrollBehaviour((x, y), '_scroll_listing'))
        else:
            self._scroll_listing(x, y)

    def _scroll_grid(self, x, y):
        """
        Callback from the animation to scroll the grid
        """
        super(SelectionGrid, self)._scroll_grid(x, y)
        self.selection.x -= x
        self.selection.y -= y

    def _scroll_listing(self, x, y):
        """
        Callback from the animation to scroll the listing
        """
        self.selection.x += x
        self.selection.y += y
        self._queue_rendering()
        self._queue_sync_properties('selection')

    def _candy_create_item(self, item_num, pos_x, pos_y):
        """
        Render one child
        """
        child = super(SelectionGrid, self)._candy_create_item(item_num, pos_x, pos_y)
        if child:
            for behaviour in self.behaviour:
                behaviour.apply(0, [child])
        return child

    def _prepare_sync(self):
        """
        Check for items to be updated based on the behaviours
        """
        super(SelectionGrid, self)._prepare_sync()
        if (self._obj and not 'selection' in self._sync_properties) or not self.behaviour:
            return
        x, y, width, height = self.selection.geometry
        # current cell position of the selection bar
        # get the items that could be affected by a behaviour and check
        # if they are covered by the selection widget
        base_x = (self.selection.x - self.items.x) / self._col_size
        base_y = (self.selection.y - self.items.y) / self._row_size
        in_area = []
        for x0 in range(-1, 2):
            for y0 in range(-1, 2):
                child = self._rendered.get((base_x + x0, base_y + y0))
                if child is None:
                    # not rendered
                    continue
                px = abs(child.x + self.items.x - x)
                py = abs(child.y + self.items.y - y)
                if px > width or py > height:
                    # not covered
                    continue
                coverage = (100 - 100 * px / width) * (100 - 100 * py / height)
                if coverage:
                    # x percent * y percent coverage
                    in_area.append((coverage, child))
        # sort by coverage and draw from the lowest
        in_area.sort(lambda x,y: cmp(x[0], y[0]))
        modified = self.items.modified
        self.items.modified = []
        for coverage, child in in_area:
            child.raise_top()
            for behaviour in self.behaviour:
                behaviour.apply(float(coverage) / 10000 * MAX_ALPHA, [child])
            if child in modified:
                modified.remove(child)
            self.items.modified.append(child)
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
