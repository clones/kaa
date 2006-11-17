# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# cpuinfo.py - Monitor CPU usage
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
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

__all__ = [ 'cpuinfo', 'USER', 'NICE', 'SYSTEM', 'IDLE', 'IOWAIT',
            'IRQ', 'SOFTIRQ', 'CURRENT_PROC' ]

# python imports
import os

# kaa imports
import kaa.notifier

_stat = None, None
_proc = None, None
_counter = 0
_cache = None

USER = 0
NICE = 1
SYSTEM = 2
IDLE = 3
IOWAIT = 4
IRQ = 5
SOFTIRQ = 6
CURRENT_PROC = -1

def _poll(pid):
    """
    poll /proc files and remeber lines we need later.
    """
    global _stat
    global _proc
    global _counter
    global _cache
    fp = open('/proc/stat')
    _stat = fp.readline(), _stat[0]
    fp.close()
    fp = open('/proc/%s/stat' % pid)
    _proc = fp.readline(), _proc[0], _timer.get_interval()
    fp.close()
    _cache = None
    if _counter == 0:
        return True
    _counter -= 1
    if _counter > 0:
        return True
    # no access for 5 seconds, slow down
    _timer.stop()
    _timer.start(1)


# when this module is imported, use it. The first valid
# information will be ready in 1 second
_timer = kaa.notifier.Timer(_poll, os.getpid())
_timer.start(1)
_poll(os.getpid())
_poll(os.getpid())

def cpuinfo():
    """
    Returns /proc/stat values and the cpu time the current process
    is using the last second.
    """
    global _cache
    if _cache:
        # nothing changed
        return _cache
    # user: normal processes executing in user mode
    # nice: niced processes executing in user mode
    # system: processes executing in kernel mode
    # idle: twiddling thumbs
    # iowait: waiting for I/O to complete
    # irq: servicing interrupts
    # softirq: servicing softirqs
    if not _stat or _stat[0] == _stat[1]:
        return 0, 0, 0, 100, 0, 0, 0, 0
    info = [ i for i in _stat[0].strip().split(' ') if i ]
    last = [ i for i in _stat[1].strip().split(' ') if i ]
    all = 0
    for i in range(1, len(info)):
        all += long(info[i]) - long(last[i])
    res = []
    for i in range(1, len(info)):
        res.append((100 * (long(info[i]) - long(last[i]))) / all)
    info = long(_proc[0].split(' ')[13]) + long(_proc[0].split(' ')[14])
    last = long(_proc[1].split(' ')[13]) + long(_proc[1].split(' ')[14])

    # FIXME: This is wrong. We need to call jiffies_to_clock_t() here
    # to convert this into seconds into percent. For me this is
    # correct because the value seems to be 100, but it could be
    # wrong. So a C wrapper is needed here I guess.
    res.append(int((info - last) / _proc[2]))

    global _counter
    if _counter == 0:
        # speed up polling
        _timer.stop()
        _timer.start(0.1)
        # poll now and in 0.1 seconds again. We set the _cache after
        # calling _poll to not mess it up
        _poll(os.getpid())
    _counter = 50
    _cache = res
    return res


if __name__ == '__main__':

    def debug():
        print cpuinfo()

    def add_load():
        x = 0
        for i in range(10000):
            x += i

    kaa.notifier.Timer(add_load).start(0.001)
    t = kaa.notifier.Timer(debug)
    t.start(1)
    kaa.notifier.OneShotTimer(t.stop).start(6)
    kaa.notifier.OneShotTimer(t.start, 1).start(15)
    kaa.main()
