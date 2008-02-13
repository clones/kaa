# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# thread.py - Thread module for the notifier
# -----------------------------------------------------------------------------
# $Id$
#
# This module contains some wrapper classes for threading while running the
# notifier main loop. It should only be used when non blocking handling is not
# possible. The main loop itself is not thread save, the the function called in
# the thread should not touch any variables inside the application which are
# not protected by by a lock.
#
# You can create a Thread object with the function and it's
# arguments. After that you can call the start function to start the
# thread. This function has an optional parameter with a callback
# which will be called from the main loop once the thread is
# finished. The result of the thread function is the parameter for the
# callback.
#
# In most cases this module is not needed, please add a good reason why you
# wrap a function in a thread.
#
# -----------------------------------------------------------------------------
# kaa.notifier - Mainloop and callbacks
# Copyright (C) 2005-2008 Dirk Meyer, Jason Tackaberry, et al.
#
# First Version: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#                Jason Tackaberry <tack@urandom.ca>
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

__all__ = [ 'MainThreadCallback', 'ThreadCallback', 'is_mainthread',
            'wakeup', 'set_as_mainthread', 'create_thread_notifier_pipe' ]

# python imports
import sys
import os
import threading
import logging
import fcntl
import socket
import errno

# notifier imports
import nf_wrapper as notifier
from callback import Callback
from signals import Signal
from async import InProgress

# get logging object
log = logging.getLogger('notifier')

class MainThreadCallback(Callback):
    def __call__(self, *args, **kwargs):
        in_progress = InProgress()

        if is_mainthread():
            try:
                result = super(MainThreadCallback, self).__call__(*args, **kwargs)
            except:
                in_progress.throw(*sys.exc_info())
            else:
                in_progress.finished(result)

            return in_progress

        _thread_notifier_queue_callback(self, args, kwargs, in_progress)

        # Return an InProgress object which the caller can connect to
        # or wait on.
        return in_progress


class ThreadInProgress(InProgress):
    def __init__(self, callback, *args, **kwargs):
        InProgress.__init__(self)
        self._callback = Callback(callback, *args, **kwargs)


    def _execute(self):
        """
        Execute the callback. This function SHOULD be called __call__ but
        InProgress.__call__ returns the result. This is deprecated but
        still used.
        """
        if self._callback is None:
            return None
        try:
            MainThreadCallback(self.finished)(self._callback())
        except:
            MainThreadCallback(self.throw)(*sys.exc_info())
        self._callback = None


    def active(self):
        """
        Return True if the callback is still waiting to be proccessed.
        """
        return self._callback is not None


    def stop(self):
        """
        Remove the callback from the thread schedule if still active.
        """
        self._callback = None


class ThreadCallback(Callback):
    """
    Notifier aware wrapper for threads. When a thread is started, it is
    impossible to fork the current process into a second one without exec both
    using the notifier main loop because of the shared _thread_notifier_pipe.
    """
    _daemon = False
    
    def wait_on_exit(self, wait=False):
        """
        Wait for the thread on application exit. Default is True.
        """
        self._daemon = not wait


    def _create_thread(self, *args, **kwargs):
        """
        Create and start the thread.
        """
        cb = Callback._get_callback(self)
        async = ThreadInProgress(cb, *args, **kwargs)
        # create thread and setDaemon
        t = threading.Thread(target=async._execute)
        t.setDaemon(self._daemon)
        # connect thread.join to the InProgress
        join = lambda *args, **kwargs: t.join()
        async.connect_both(join, join)
        # start the thread
        t.start()
        return async


    def _get_callback(self):
        """
        Return callable for this Callback.
        """
        return self._create_thread


    
def is_mainthread():
    """
    Return True if the caller is in the main thread right now.
    """
    # If threading module is None, assume main thread.  (Silences pointless
    # exceptions on shutdown.)
    return (not threading) or threading.currentThread() == _thread_notifier_mainthread


_thread_notifier_mainthread = threading.currentThread()
_thread_notifier_lock = threading.Lock()
_thread_notifier_queue = []

# For MainThread* callbacks. The pipe will be created when it is used the first
# time. This solves a nasty bug when you fork() into a second notifier based
# process without exec. If you have this pipe, communication will go wrong.
# (kaa.utils.daemonize does not have this problem.)
_thread_notifier_pipe = None

    
def wakeup():
    """
    Wake up main thread.
    """
    if _thread_notifier_pipe and len(_thread_notifier_queue) == 0:
        os.write(_thread_notifier_pipe[1], "1")


def create_thread_notifier_pipe(new = True, purge = False):
    """
    Creates a new pipe for the thread notifier.  If new is True, a new pipe
    will always be created; if it is False, it will only be created if one
    already exists.  If purge is True, any previously queued work will be
    discarded.

    This is an internal function, but we export it for kaa.utils.daemonize.
    """
    global _thread_notifier_pipe
    log.info('create thread notifier pipe')

    if not _thread_notifier_pipe and not new:
        return
    elif _thread_notifier_pipe:
        # There is an existing pipe already, so stop monitoring it.
        notifier.socket_remove(_thread_notifier_pipe[0])

    if purge:
        del _thread_notifier_queue[:]

    _thread_notifier_pipe = os.pipe()
    fcntl.fcntl(_thread_notifier_pipe[0], fcntl.F_SETFL, os.O_NONBLOCK)
    fcntl.fcntl(_thread_notifier_pipe[1], fcntl.F_SETFL, os.O_NONBLOCK)
    notifier.socket_add(_thread_notifier_pipe[0], _thread_notifier_run_queue)

    if _thread_notifier_queue:
        # A thread is already running and wanted to run something in the
        # mainloop before the mainloop is started. In that case we need
        # to wakeup the loop ASAP to handle the requests.
        os.write(_thread_notifier_pipe[1], "1")


def set_as_mainthread():
    global _thread_notifier_mainthread
    _thread_notifier_mainthread = threading.currentThread()
    if not _thread_notifier_pipe:
        # Make sure we have a pipe between the mainloop and threads. Since
        # loop() calls set_as_mainthread it is safe to assume the loop is
        # connected correctly. If someone calls step() without loop() and
        # without set_as_mainthread inter-thread communication does not work.
        create_thread_notifier_pipe()
    

def _thread_notifier_queue_callback(callback, args, kwargs, in_progress):
    _thread_notifier_lock.acquire()
    _thread_notifier_queue.append((callback, args, kwargs, in_progress))
    if len(_thread_notifier_queue) == 1:
        if _thread_notifier_pipe:
            os.write(_thread_notifier_pipe[1], "1")
    _thread_notifier_lock.release()


def _thread_notifier_run_queue(fd):
    global _thread_notifier_queue
    try:
        os.read(_thread_notifier_pipe[0], 1000)
    except socket.error, (err, msg):
        if err == errno.EAGAIN:
            # Resource temporarily unavailable -- we are trying to read
            # data on a socket when none is avilable.  This should not
            # happen under normal circumstances, so log an error.
            log.error("Thread notifier pipe woke but no data available.")
    except OSError:
        pass

    while _thread_notifier_queue:
        _thread_notifier_lock.acquire()
        callback, args, kwargs, in_progress = _thread_notifier_queue.pop(0)
        _thread_notifier_lock.release()

        try:
            in_progress.finished(callback(*args, **kwargs))
        except:
            in_progress.throw(*sys.exc_info())

    return True
