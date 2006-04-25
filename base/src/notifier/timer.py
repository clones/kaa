# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# timer.py - Timer classes for the notifier
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa-notifier - Notifier Wrapper
# Copyright (C) 2005 Dirk Meyer, et al.
#
# First Version: Dirk Meyer <dmeyer@tzi.de>
# Maintainer:    Dirk Meyer <dmeyer@tzi.de>
#
# Please see the file doc/AUTHORS for a complete list of authors.
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

__all__ = [ 'Timer', 'WeakTimer', 'OneShotTimer', 'WeakOneShotTimer' ]

import logging

from callback import NotifierCallback, WeakNotifierCallback, notifier
from thread import MainThreadCallback, is_mainthread

# get logging object
log = logging.getLogger('notifier')

class Timer(NotifierCallback):

    def __init__(self, callback, *args, **kwargs):
        super(Timer, self).__init__(callback, *args, **kwargs)
        self.restart_when_active = True
        self._interval = None


    def start(self, interval):
        if not is_mainthread():
            return MainThreadCallback(self.start, interval)()

        if self.active():
            if not self.restart_when_active:
                return
            self.unregister()

        self._id = notifier.timer_add(int(interval * 1000), self)
        self._interval = interval


    def stop(self):
        if not is_mainthread():
            return MainThreadCallback(self.stop)()
        self.unregister()


    def unregister(self):
        if self.active():
            notifier.timer_remove(self._id)
            super(Timer, self).unregister()


    def get_interval(self):
        return self._interval


    def __call__(self, *args, **kwargs):
        if not self.active():
            # This happens if previous timer that has been called during the
            # same notifier step has stopped us.  This is a workaround to a
            # bug that exists in notifier.
            log.debug('calling callback on inactive timer (%s)' % repr(self))
            return False

        return super(Timer, self).__call__(*args, **kwargs)


class OneShotTimer(Timer):
    """
    A Timer that onlt gets executed once. If the timer is started again
    inside the callback, make sure 'False' is NOT returned or the timer
    will be removed again without being called. To be on tge same side,
    return nothing in such a callback.
    """
    def __call__(self, *args, **kwargs):
        self.unregister()
        super(Timer, self).__call__(*args, **kwargs)
        return False



class WeakTimer(WeakNotifierCallback, Timer):
    pass

class WeakOneShotTimer(WeakNotifierCallback, OneShotTimer):
    pass

