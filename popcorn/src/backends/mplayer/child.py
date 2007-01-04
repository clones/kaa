import kaa.notifier

# start mplayer in gdb for debugging
USE_GDB = False


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
        # print self._func, cmd
        self._app._child.write(cmd.strip() + '\n')


class MplayerApp(object):

    def __init__(self, command=None):
        if not command:
            return
        if USE_GDB:
            self._child = kaa.notifier.Process("gdb")
            self._command = command
        else:
            self._child = kaa.notifier.Process(command)
        self.signals = self._child.signals
        stop = kaa.notifier.WeakCallback(self._child_stop)
        self._child.set_stop_command(stop)
                
    def start(self, args):
        if USE_GDB:
            self._child.start(self._command)
            self._child.write("run %s\n" % ' '.join(args))
            self._child.signals["stdout"].connect_weak(self._child_handle_line)
            self._child.signals["stderr"].connect_weak(self._child_handle_line)
        else:
            self._child.start(args)


    def _child_stop(self):
        self.quit()
        # Could be paused, try sending again.
        self.quit()


    def _child_handle_line(line):
        if line.startswith("Program received signal SIGSEGV"):
            # Mplayer crashed, issue backtrace.
            self._child.write("thread apply all bt\n")
            

    def stop(self):
        self._child.stop()


    def is_alive(self):
        return self._child and self._child.is_alive()
    

    def __getattr__(self, attr):
        """
        Return ChildCommand object.
        """
        return ChildCommand(self, attr)
