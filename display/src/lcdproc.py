# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# lcdproc.py - LCDProc Interface
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.display - Generic Display Module
# Copyright (C) 2006-2008 Dirk Meyer, Jason Tackaberry
#
# First Edition: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
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

__all__ = [ 'LCD' ]

# python imports
import os
import socket
import logging

# kaa imports
import kaa

# get logging object
log = logging.getLogger('lcd')


class Widget(object):
    """
    Widget on a screen.
    """
    def __init__(self, screen, id, type):
        self.screen = screen
        self.id = id
        self.type = type

    def set(self, *args):
        self.screen.widget_set(self.type, self.id, *args)


class Screen(object):
    """
    LCD Screen with widgets.
    """
    def __init__(self, lcd, name, priority='foreground', duration=0):
        self._send = lcd
        self.width, self.height, self.size = lcd.width, lcd.height, lcd.size
        self.name = name
        self._priority = priority
        self._duration = duration
        self._send = lcd._send
        self._send('screen_add %s' % name)
        self._send('screen_set %s name %s' % (name, name))
        self._send('screen_set %s -priority %s -heartbeat off' % \
                   (name, priority))
        if duration:
            self._send('screen_set %s -timeout %s' % (name, duration*8))
        self.widgets = []
        self.nextid = 0


    def get_priority(priority):
        """
        Get screen priority.
        """
        return self._priority


    def set_priority(self, priority):
        """
        Set screen priority.
        """
        self._send('screen_set %s -priority %s' % (self.name, priority))
        self._priority = priority


    def widget_add(self, type, *args):
        """
        Add a widget. Arguments are based on the type.

        string x y text
            Displays text at position (x,y).

        title text
            Uses text as the title to display.

        hbar x y length
            Displays a horizontal starting at position (x,y) that is length
            pixels wide.

        vbar x y length
            Displays a vertical starting at position (x,y) that is length
            pixels high.

        icon x y iconname
            Displays the icon iconname at position (x,y).

        scroller left top right bottom direction speed text
            Displays a scroller spanning from position (left,top) to
            (right,bottom) scrolling text in horizontal (h), vertical
            (v) or marquee (m) direction at a speed of speed, which is
            the number of movements per rendering stroke (8
            times/second).

        frame left top right bottom width height direction speed
            Sets up a frame spanning from (left,top) to (right,bottom)
            that is width columns wide and height rows high. It
            scrolls in either horizontal (h) or vertical (v) direction
            at a speed of speed, which is the number of movements per
            rendering stroke (8 times/second).

        num x int
            Displays decimal digit int at the horizontal position x,
            which is a normal character x coordinate on the
            display. The special value 10 for int displays a colon.
        """
        self.nextid += 1
        id = self.nextid
        self._send('widget_add %s %s %s' % (self.name, id, type))
        self.widgets.append(id)
        if args:
            self.widget_set(type, id, *args)
        return Widget(self, id, type)


    def widget_set(self, type, id, *args):
        """
        Changes attributes of a widget. See widget_add for details.
        """
        args = list(args)
        if type == 'scroller' and len(args[-1]) > self.width and \
               not args[-1][-1] in ' -_':
            # looks better
            args[-1] += '     '

        if type in ('string', 'title', 'scroller'):
            if isinstance(args[-1], unicode):
                a = kaa.unicode_to_str(args[-1])
            args[-1] = '"%s"' % args[-1].replace('"', '\\"').replace('\n', '')
        self._send('widget_set %s %s %s' % \
                   (self.name, id, ' '.join([str(i) for i in args ])))


    def widget_del(self, widget):
        """
        Deleted a widget from the screen.
        """
        if isinstance(widget, Widget):
            widget = widget.id
        if not widget in self.widgets:
            return
        self._send('widget_del %s %s' % (self.name, widget))
        self.widgets.remove(widget)


    def wipe(self):
        """
        Clear the screen.
        """
        while self.widgets:
            self.widget_del(self.widgets[0])


    def __del__(self):
        """
        Destructor. It will wipe the screen and remove it from
        the lcd.
        """
        if not self._duration:
            self.wipe()
            self._send('screen_del %s' % self.name)


class LCD(object):
    """
    LCD interface
    """
    def __init__(self, server='127.0.0.1', port=13666):
        self.signals = {
            'connected': kaa.Signal()
        }
        self._connect(server, port)
        self._screenno = 0


    def create_screen(self, name = None, priority='foreground', duration=0):
        """
        Create a new screen with the given name.
        """
        if not name:
            name = 'lcd%d' % self._screenno
            self._screenno += 1
        return Screen(self, name, priority, duration)


    def _send(self, line):
        """
        Send a command to the server.
        """
        self.socket.write(line + '\n')


    @kaa.coroutine()
    def _connect(self, server, port):
        """
        Connect to the server and init the connection.
        """
        self.socket = kaa.Socket()
        try:
            yield self.socket.connect((server, port))
        except Exception, e:
            # try again later
            log.error('LCDproc connection error; will try again later')
            kaa.OneShotTimer(self._connect, server, port).start(10)
            yield False
        self._send('hello')
        wait = kaa.inprogress(self.socket.signals['read'])
        line = (yield wait).strip().split()
        self._send('client_set name kaa')
        self.size = int(line[7]), int(line[9])
        self.width, self.height = self.size
        log.info('LCDproc connected')
        self.signals['connected'].emit(self.width, self.height)
        yield False
