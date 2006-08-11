import os
import sys
import fcntl
import kaa.notifier

from kaa.weakref import weakref

class ChildCommand(object):
    def __init__(self, fd, cmd):
        self._fd = fd
        self._cmd = cmd

    def __call__(self, *args, **kwargs):
        self._fd(repr((self._cmd, args, kwargs)) + "\n")

        
class ChildProcess(object):
    def __init__(self, parent, *args):
        # Launch (-u is unbuffered stdout)
        self._parent = weakref(parent)
        self._child = kaa.notifier.Process([sys.executable, '-u'] + list(args))
        self._child.signals["stdout"].connect_weak(self._handle_line)
        self._child.signals["stderr"].connect_weak(self._handle_line)

    def start(self):
        self._child.start()

    def _handle_line(self, line):
        if line and line[0] == "!":
            command, args, kwargs = eval(line[1:])
            getattr(self._parent, "_child_" + command)(*args, **kwargs)
        else:
            print "CHILD[%d]: %s" % (self._child.child.pid, line)

    def __getattr__(self, attr):
        if attr in ('signals', 'set_stop_command'):
            return getattr(self._child, attr)
        return ChildCommand(self._child.write, attr)

    
class ParentCommand(object):
    def __init__(self, cmd):
        self._cmd = cmd

    def __call__(self, *args, **kwargs):
        sys.stderr.write("!" + repr( (self._cmd, args, kwargs) ) + "\n")

        
class Parent(object):

    def __getattr__(self, attr):
        return ParentCommand(attr)


class Player(object):
    def __init__(self):
        monitor = kaa.notifier.WeakSocketDispatcher(self._handle_line)
        monitor.register(sys.stdin.fileno())
        flags = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)
        self._stdin_data = ''
        self.parent = Parent()
    

    def _handle_line(self):
        data = sys.stdin.read()
        if len(data) == 0:
            # Parent likely died.
            self._handle_command_die()
        self._stdin_data += data
        while self._stdin_data.find('\n') >= 0:
            line = self._stdin_data[:self._stdin_data.find('\n')]
            self._stdin_data = self._stdin_data[self._stdin_data.find('\n')+1:]
            command, args, kwargs = eval(line)
            reply = getattr(self, command)(*args, **kwargs)
