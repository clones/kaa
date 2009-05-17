# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# cpuinfo.py - Monitor CPU usage
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006-2008 Dirk Meyer
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

__all__ = [ 'cpuinfo', 'check', 'USER', 'NICE', 'SYSTEM', 'IDLE', 'IOWAIT',
            'IRQ', 'SOFTIRQ', 'CURRENT_PROC' ]

# python imports
import os
import time

# kaa imports
import kaa

_stat = None, None
_proc = None, None
_last_request_time = None
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
    global _stat, _proc, _cache
    _stat = [line for line in file('/proc/stat') if line.startswith('cpu')], _stat[0]
    _proc = file('/proc/%s/stat' % pid).readline(), _proc[0], _timer.interval
    _cache = None
    if not _last_request_time:
        return True

    delta = time.time() - _last_request_time
    if _timer.interval < 1 and delta > 3:
        # CPU time hasn't been requested in the past 3 seconds, so slow
        # timer down.
        _timer.stop()
        _timer.start(1)
    elif _timer.interval == 1 and delta > 10:
        # CPU time hasn't been requested in the past 10 seconds.  Disable
        # polling.
        return False


# Timer that polls cpu stats.  Started on demand.
_timer = kaa.Timer(_poll, os.getpid())

def cpuinfo():
    """
    Returns /proc/stat values and the cpu time the current process
    is using the last second.
    """
    global _cache, _last_request_time
    if _cache:
        # nothing changed
        return _cache
    elif not _timer.active():
        # First call to cpuinfo() (either ever or since poll timer got
        # stopped), so take initial measurements and start timer now.
        _last_request_time = time.time()
        _timer.start(1)
        _poll(os.getpid())
        _poll(os.getpid())

    # user: normal processes executing in user mode
    # nice: niced processes executing in user mode
    # system: processes executing in kernel mode
    # idle: twiddling thumbs
    # iowait: waiting for I/O to complete
    # irq: servicing interrupts
    # softirq: servicing softirqs
    noinfo = 0, 0, 0, 100, 0, 0, 0, 0, 0, 0
    if None in _stat:
        return [noinfo]

    res = []
    for n, (l_info, l_last) in enumerate(zip(_stat[0], _stat[1])):
        info = [float(i) for i in l_info.strip().split(' ')[1:] if i]
        last = [float(i) for i in l_last.strip().split(' ')[1:] if i]
        if info == last:
            res.append(noinfo)
            continue

        total = sum(i-l for i,l in zip(info, last))
        res.append([100 * (i-l) / total for i,l in zip(info, last)])

        info = sum(float(n) for n in _proc[0].split(' ')[13:15])
        last = sum(float(n) for n in _proc[1].split(' ')[13:15])

        if n == 0:
            # FIXME: This is wrong. We need to call jiffies_to_clock_t() here
            # to convert this into seconds into percent. For me this is
            # correct because the value seems to be 100, but it could be
            # wrong. So a C wrapper is needed here I guess.
            res[-1].append((info - last) / _proc[2])

    if time.time() - _last_request_time < 2 and _timer.interval != 0.2:
        # CPU time is being requested a lot, so increase poll timer frequency
        # to get a more accurate reading.
        _timer.stop()
        _timer.start(0.2)
        # poll now and in 0.2 seconds again. We set the _cache after
        # calling _poll to not mess it up
        _poll(os.getpid())
    _last_request_time = time.time()
    _cache = res
    return res


def check(user=None, nice=None, sys=None, all=None, nonnice=None, idle=None, io=None):
    info = cpuinfo()[0]

    if (user is not None and info[USER] >= user) or \
       (nice is not None and info[NICE] >= nice) or \
       (sys is not None and info[SYSTEM] >= sys) or \
       (all is not None and info[USER] + info[NICE] + info[SYSTEM] >= all) or \
       (nonnice is not None and info[USER] + info[SYSTEM] >= nonnice) or \
       (idle is not None and info[IDLE] < idle) or \
       (io is not None and info[IOWAIT] >= io):
        return True
    return False


if __name__ == '__main__':

    def debug():
        print '-----------------'
        for n, info in enumerate(cpuinfo()):
            print '%d.  cpu=%.2f  idle=%.2f  io=%.2f' % (n, sum(info[:3]), info[IDLE], info[IOWAIT])

    @kaa.coroutine()
    def add_load():
        x = 0
        for i in range(300000):
            yield kaa.NotFinished
        print "Done load generation"

    add_load()
    t = kaa.Timer(debug)
    t.start(0.5)
    #kaa.OneShotTimer(t.stop).start(4)
    #kaa.OneShotTimer(t.start, 1).start(10)
    kaa.main.run()
