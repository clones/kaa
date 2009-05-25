# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# mplayer/child.py - mplayer child wrapper
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.popcorn - Generic Player API
# Copyright (C) 2006 Jason Tackaberry, Dirk Meyer
#
# Please see the file AUTHORS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'ChildProcess' ]


# python imports
import logging

# kaa imports
import kaa

# get logging object
log = logging.getLogger('popcorn.mplayer')

class Arguments(list):
    """
    Argument list.
    """
    def __init__(self, args=()):
        if args:
            args = args.split(' ')
        list.__init__(self, args)


    def add(self, **kwargs):
        """
        Add -key=value arguments.
        """
        for key, value in kwargs.items():
            if value is None:
                continue
            self.extend(('-' + key.replace('_', '-'), str(value)))


class ChildCommand(object):
    """
    A command or message for the child.
    """
    def __init__(self, app, cmd):
        self._app = app
        self._cmd = cmd


    def __call__(self, *args):
        """
        Send command to child.
        """
        if not self._app.is_alive():
            return
        cmd = '%s %s' % (self._cmd, ' '.join([ str(x) for x in args]))
        log.debug('send %s', cmd)
        self._app._child.write(cmd.strip() + '\n')


class ChildProcess(object):
    """
    Mplayer child wrapper,
    """
    def __init__(self, command=None, gdb = False):
        # create argument list
        self._gdb = gdb
        # Do not add -framedrop to this list, mplayer has issues with some
        # codecs.
        self.args = Arguments("-v -slave -osdlevel 0 -nolirc -nojoystick -fixed-vo -identify -nodouble")
        self.filters = []
        if not command:
            return
        if self._gdb:
            self._child = kaa.Process("gdb")
            self._command = command
        else:
            self._child = kaa.Process(command)
        self.signals = self._child.signals
        stop = kaa.WeakCallback(self._child_stop)
        self._child._stop_command = stop


    def start(self, media):
        args = self.args[:]
        if self.filters:
            args.extend(('-vf', ",".join(self.filters)))

        # add extra file arguments
        args.extend(media.mplayer_args)

        log.info("spawn: %s %s", self._mp_cmd, ' '.join(args))

        if self._gdb:
            signal = self._child.start(self._command)
            self._child.write("run %s\n" % ' '.join(args))
            self._child.signals['readline'].connect_weak(self._child_handle_line)
            return signal
        return self._child.start(args)


    def _child_stop(self):
        self.quit()
        # Could be paused, try sending again.
        self.quit()


    def _child_handle_line(self, line):
        if line.startswith("Program received signal"):
            # Mplayer crashed, issue backtrace.
            self._child.write("thread apply all bt\nquit\n")
        elif line.startswith("Program exited"):
            self._child.write("quit\n")


    def stop(self):
        self._child.stop()


    def is_alive(self):
        return self._child and self._child.alive


    def __getattr__(self, attr):
        """
        Return ChildCommand object.
        """
        return ChildCommand(self, attr)
