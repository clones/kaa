# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# ipc.py - IPC for kaa.popcorn and childs
# -----------------------------------------------------------------------------
# $Id$
#
# This module defines some code that makes communication between the parent
# process and a forked python based proces much easier.
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

__all__ = [ 'ChildProcess', 'Player' ]

# python imports
import os
import sys
import fcntl
import logging

# kaa imports
import kaa.notifier
from kaa.weakref import weakref

# get logging objects
log = logging.getLogger('popcorn.ipc')
childlog = logging.getLogger('popcorn.child')

class ChildCommand(object):
    """
    A command or message for the child.
    """
    def __init__(self, fd, cmd):
        self._fd = fd
        self._cmd = cmd


    def __call__(self, *args, **kwargs):
        """
        Send command to child.
        """
        log.debug('Send IPC to child: %s %s %s' % (self._cmd, args, kwargs))
        self._fd(repr((self._cmd, args, kwargs)) + "\n")


class ChildProcess(object):
    """
    A child process with communication helpers.
    """
    def __init__(self, parent, script, gdb=False):
        # Launch (-u is unbuffered stdout)
        self._parent = weakref(parent)

        if gdb:
            self._child = kaa.notifier.Process("gdb")
            self._gdb = script
        else:
            self._child = kaa.notifier.Process([sys.executable, '-u', script])
            self._gdb = None
        self._child.signals["stdout"].connect_weak(self._handle_line)
        self._child.signals["stderr"].connect_weak(self._handle_line)
        self._name = os.path.basename(os.path.dirname(script))


    def start(self, *args):
        """
        Start child.
        """
        if not self._gdb:
            return self._child.start(args)
        self._child.start(sys.executable)
        self._child.write("run -u %s %s\n" % (self._gdb, ' '.join(args)))


    def _handle_line(self, line):
        """
        Handle line from child.
        """
        if not line:
            return True
        
        if line.startswith("!kaa!"):
            # ipc command from child
            command, args, kwargs = eval(line[5:])
            cmd = getattr(self._parent, "_child_" + command, None)
            log.debug('Receive IPC from child: %s %s %s' % (command, args, kwargs))
            if cmd:
                cmd(*args, **kwargs)
                return True
            if command.startswith('set_'):
               if hasattr(self._parent, command[3:]) and args:
                   setattr(self._parent, command[3:], args[0])
                   return True
               if hasattr(self._parent, command[4:]) and args:
                   setattr(self._parent, command[4:], args[0])
                   return True
            raise AttributeError('parent has no attribute %s', command)

        if self.gdb and line.startswith("Program received signal SIGSEGV"):
            self._child.write("thread apply all bt\n")
            self._child.write("quit\n")
            return

        # do some nice debug. use the log level from child if we can detect it
        delim = line.find(' ')
        function = childlog.debug
        if delim > 0:
            function = getattr(childlog, line[:delim].lower(), childlog.debug)
            if function:
                line = line[delim+1:]
        function("[%s-%d] %s", self._name, self._child.child.pid, line)


    def __getattr__(self, attr):
        """
        Return ChildCommand object.
        """
        if attr in ('signals', 'set_stop_command'):
            return getattr(self._child, attr)
        return ChildCommand(self._child.write, attr)


class ParentCommand(object):
    """
    A command for the parent.
    """
    def __init__(self, cmd):
        self._cmd = cmd


    def __call__(self, *args, **kwargs):
        """
        Send command to parent.
        """
        sys.stderr.write("!kaa!" + repr( (self._cmd, args, kwargs) ) + "\n")


class Parent(object):
    """
    Object representing the parent.
    """
    def __getattr__(self, attr):
        return ParentCommand(attr)


class ConfigDict(dict):
    def __getattr__(self, attr):
        return self[attr]

    
class Player(object):
    """
    Child app player. The object has a memeber 'parent' to send commands
    to the parent and need to implement the function the parent is calling.
    """
    def __init__(self):
        monitor = kaa.notifier.WeakSocketDispatcher(self._handle_line)
        monitor.register(sys.stdin.fileno())
        flags = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)
        self._stdin_data = ''
        self.config = None
        self.parent = Parent()


    def set_config(self, config):
        """
        set config object
        """
        def _convert(d):
            r = ConfigDict(d)
            for key, value in r.items():
                if isinstance(value, dict):
                    r[key] = _convert(value)
            return r
        self.config = _convert(config)

        
    def _handle_line(self):
        """
        Handle data from stdin.
        """
        data = sys.stdin.read()
        if len(data) == 0:
            # Parent likely died.
            self._handle_command_die()
        self._stdin_data += data
        while self._stdin_data.find('\n') >= 0:
            line = self._stdin_data[:self._stdin_data.find('\n')]
            self._stdin_data = self._stdin_data[self._stdin_data.find('\n')+1:]
            command, args, kwargs = eval(line)
            log.debug('Receive IPC from parent: %s %s %s' % (command, args, kwargs))
            reply = getattr(self, command)(*args, **kwargs)


    def die(self):
        sys.exit(0)
        
