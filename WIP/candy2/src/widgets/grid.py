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

# clutter imports
import clutter

# kaa.candy imports imports
import core
from .. import candyxml, timeline

# get logging object
log = logging.getLogger('kaa.candy')

class ScrollBehaviour(clutter.Behaviour):
    __gtype_name__ = 'GridScroll'

    def __init__ (self, widget, start, stop, secs):
        clutter.Behaviour.__init__(self)
        self._timeline = timeline.Timeline(secs)
        self._alpha = clutter.Alpha(self._timeline, clutter.ramp_inc_func)
        self.set_alpha(self._alpha)
        self._start = start
        self._diff = stop - start
        self._current = start
        self.apply(widget)
        self._timeline.start()

    def is_playing(self):
        return self._timeline.is_playing()

    def stop(self):
        self._timeline.stop()
        return self._diff - (self._current - self._start)

    def do_alpha_notify(self, alpha_value):
        alpha = float(alpha_value) / clutter.MAX_ALPHA
        current = self._start + int(self._diff * alpha)
        step = self._current - current
        self._current = current
        for actor in self.get_actors():
            actor._set_scroll_step(current, step)

class Grid(core.Group):
    """
    Grid Widget
    @note: see C{test/flickr.py} for an example
    @todo: add anaimation support to move inside the grid
    @todo: add parameter to sort items x or y first
    """
    candyxml_name = 'grid'
    context_sensitive = True

    HORIZONTAL, VERTICAL =  range(2)

    def __init__(self, pos, size, cell_size, cell_item, items, template,
                 orientation, start=0, context=None):
        """
        Simple grid widget to show the items based on the template.
        @param pos: (x,y) position of the widget or None
        @param size: (width,height) geometry of the widget or None.
        @param cell_size: (width,height) of each cell
        @param cell_item: string how the cell item should be added to the context
        @param items: list of objects or object name in the context
        @param template: child template for each cell
        @param orientation: how to arange the grid: Grid.HORIZONTAL or Grid.VERTICAL
        @param start: start row/col of the grid
        @param context: the context the widget is created in
        """
        super(Grid, self).__init__(pos, size, context)
        # clip the grid to hide cells moved outside the visible area
        self.set_clip(0, 0, *size)
        if isinstance(items, (str, unicode)):
            # items is a string, get it from the context
            self.set_dependency(items)
            items = eval(items, context)
        # store arguments for later public use
        self.orientation = orientation
        self.cell_size = cell_size
        # do some calculations
        self.num_cols = size[0] / cell_size[0]
        self.num_rows = size[1] / cell_size[1]
        self._padx = size[0] /self.num_cols - cell_size[0]
        self._pady = size[1] /self.num_rows - cell_size[1]
        self._rendered = []
        self._scroll_animation = None
        self._current = start
        # store arguments for later private use
        self._items = items
        self._cell_item = cell_item
        self._template = template
        # set line_size (col_size or row_size) and draw the visible area
        if self.orientation == Grid.HORIZONTAL:
            self._line_size = self.cell_size[0] + self._padx
            for col in range(self.num_cols):
                self._render_line(col + start, -start * self._line_size)
        if self.orientation == Grid.VERTICAL:
            self._line_size = self.cell_size[1] + self._pady
            for row in range(self.num_rows):
                self._render_line(row + start, -start * self._line_size)

    def destroy(self):
        """
        Destroy the widget by stopping running animations.
        """
        if self._scroll_animation and self._scroll_animation.is_playing():
            self._scroll_animation.stop()
        self._scroll_animation = None
        super(Grid, self).destroy()

    def scroll(self, cells, secs):
        """
        Scroll by cells rows or cols based on the orientation
        """
        skip = 0
        if self._scroll_animation and self._scroll_animation.is_playing():
            skip = self._scroll_animation.stop()
        start = self._current * self._line_size - skip
        self._current += cells
        stop = self._current * self._line_size
        self._scroll_animation = ScrollBehaviour(self, start, stop, secs)

    def _render_line(self, num, delta=0):
        """
        Render one line (row or col based on orientation)
        """
        if num < 0:
            # this makes no sense
            return
        self._rendered.append(num)
        x = self._padx / 2
        y = self._pady / 2
        if self.orientation == Grid.HORIZONTAL:
            x +=  self._line_size * num + delta
            line = self.num_rows
        if self.orientation == Grid.VERTICAL:
            y +=  self._line_size * num + delta
            line = self.num_cols
        context = copy.copy(self.get_context())
        for item in self._items[num*line:(num+1)*line]:
            context[self._cell_item] = item
            child = self._template(x=x, y=y, size=self.cell_size, context=context)
            child.set_parent(self)
            if self.orientation == Grid.HORIZONTAL:
                y += self.cell_size[1] + self._pady
            if self.orientation == Grid.VERTICAL:
                x += self.cell_size[0] + self._padx

    def _set_scroll_step(self, current, step):
        """
        Callback from the animation
        """
        # move children
        move = [ step, 0 ]
        if self.orientation == Grid.VERTICAL:
            move.reverse()
        for child in self.get_children():
            child.move_by(*move)
        cell_size = self.cell_size[self.orientation]
        min_needed = current / cell_size
        if not min_needed in self._rendered:
            self._render_line(min_needed, - current)
        max_needed = (self.get_max_size()[self.orientation] + current) / cell_size - 1
        if not max_needed in self._rendered:
            self._render_line(max_needed, -current)

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
            orientation=orientation, start=int(element.start or 0))

# register widget to candyxml
Grid.candyxml_register()
