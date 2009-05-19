# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# scheduler.py - Monitor system load and determine task intervals bsaed on
#                specified policies.
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# kaa.beacon.server - A virtual filesystem with metadata
# Copyright (C) 2006-2008 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
#    Maintainer: Dirk Meyer <dischi@freevo.org>
#                Jason Tackaberry <tack@urandom.ca>
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

__all__ = [ 'check', 'next'  ]

# python imports
import os
import time
import logging
import math

# kaa imports
import kaa

log = logging.getLogger('beacon.scheduler')

# history indices
SAMPLE = 0
TIMESTAMP = 1

# Sample indices 
AGGR = 0
AVG = 1
CPU0 = 2
CPU1 = 3
CPU2 = 4
CPU3 = 5

# Aggregate row indices
MIN_CPU = 0
MIN_NONNICE = 1
MAX_IO = 2
SELF = 3

# Average row indices
USER = 0
NICE = 1
SYSTEM = 2
IDLE = 3
IOWAIT = 4
IRQ = 5
SOFTIRQ = 6
CURRENT_PROC = -1


def to_longs(line, start=0):
    return [long(i) for i in line.strip().split(' ')[start:] if i]


class Scheduler(object):
    """
    A SMP-aware scheduler that implements the scheduler policies outlined in
    config.cxml.

    Users of the schedule will call the next() method, passing it the name of
    a policy, and next() will then return a recommended delay (in seconds) for
    the caller to sleep in order to conform to the policy's parameters.

    The scheduler is also aware of threads and forked processes and takes their
    cpu usage into account.  So if the policy says that, for example, the
    beacon-daemon cannot exceed 50% cpu, the aggregate of all beacon-daemon
    processes and threads are considered.
    """
    def __init__(self, pid_or_procname):
        # This is a wholly internal class, so don't bother prefixing members
        # with _

        # Last samples
        self.last_stat = None
        self.last_proc = None
        # Timestamp of last sample
        self.last_time = None
        # Result from last next(), 2-tuple of (wait, timestamp_of_call)
        self.cache = None
        # Timestamp of the last time the user requested cpu info.
        self.last_request_time = None
        # 2-tuples (sample, timestamp) of the last 10 deltas.  Each sample is a
        # list of rows, where row 0 (the "aggregate" row) is [min_cpu,
        # min_nonnice, max_io, proc_cpu], row 1 is the average across all cpus,
        # and the remaining rows are per-core.
        self.history = []

        self.poll_timer = kaa.WeakTimer(self.poll)
        self.pids_timer = kaa.WeakTimer(self.get_pids)

        if isinstance(pid_or_procname, (int, long)) or pid_or_procname.isdigit():
            # Pid specified.
            self.pids = [int(pid_or_procname)]
        else:
            self.procname = pid_or_procname
            self.get_pids()
            # Find all pids for this procname every 10 seconds, in case we
            # something changes.
            self.pids_timer.start(10)


    def get_pids(self):
        """
        Returns a list of pids (including threads) whose cmdline begins with procname.
        """
        all = [long(pid) for pid in os.listdir('/proc') if pid.isdigit()]
        scanned = set(all)
        matched = []
        while all:
            pid = all.pop(0)
            try:
                if not file('/proc/%d/cmdline' % pid).readline().startswith(self.procname):
                    continue
                matched.append(pid)
                tids = [long(tid) for tid in os.listdir('/proc/%d/task' % pid) if long(tid) not in scanned]
            except (IOError, OSError):
                continue

            all.extend(tids)
            scanned.update(tids)

        self.pids = matched


    def poll(self):
        """
        Polls /proc/stat and /proc/<pid>/stat foreach pid in the group,
        then calculates the delta from the last poll and stores that in
        the history list.
        """
        t = time.time()
        now_stat = [to_longs(line, 1) for line in file('/proc/stat') if line.startswith('cpu')]

        # Sum the utime+stime (in jiffies) of all processes in self.pids
        now_proc = 0
        for pid in self.pids[:]:
            try:
                now_proc += sum(to_longs(file('/proc/%s/stat' % pid).readline(), 13)[:2])
            except IOError:
                # Process went away.
                self.pids.remove(pid)

        if self.last_stat:
            sample = [None]
            for now_row, last_row in zip(now_stat, self.last_stat):
                total = sum(n-l for n,l in zip(now_row, last_row))
                if total > 0:
                    sample.append([100.0 * (i-l) / total for i,l in zip(now_row, last_row)])
                else:
                    # Fully idle.
                    sample.append((0, 0, 0, 100, 0, 0, 0, 0, 0, 0))

            max_io = max(i[IOWAIT] for i in sample[CPU0:])
            # Take the most idle core, because the OS can alawys schedule on that one.
            min_cpu = min(i[USER] + i[NICE] + i[SYSTEM] for i in sample[CPU0:])
            min_nonnice = min(i[USER] + i[SYSTEM] for i in sample[CPU0:])

            # FIXME: This is wrong. We need to call jiffies_to_clock_t() here
            # to convert this into seconds into percent. For me this is
            # correct because the value seems to be 100, but it could be
            # wrong. So a C wrapper is needed here I guess.
            proc_cpu = (now_proc - self.last_proc) / (t - self.last_time)

            sample[AGGR] = (min_cpu, min_nonnice, max_io, proc_cpu)

            if len(self.history) == 10:
                self.history.pop(0)
            self.history.append((sample, t))

        if t - self.last_request_time > 20:
            # CPU time hasn't been requested in the past 20 seconds.  Disable
            # polling.
            self.history = []
            self.last_stat = self.last_proc = self.last_time = None
            return False
        
        self.last_stat = now_stat
        self.last_proc = now_proc
        self.last_time = t


    def slope(self, row, col):
        """
        Returns the slope of the linear regression (least squares) for all
        datapoints in the history for the given row/col in the history sample.

        For example, slope(0, 3) would return the best-fit slope of the max IOWAIT
        over the history period.
        """
        n = len(self.history)
        t0 = self.history[0][TIMESTAMP]

        if n < 2:
            return 0
        elif n == 2:
            # Just two data points, so take the slope of those two points.
            return (self.history[-1][SAMPLE][row][col] - self.history[0][SAMPLE][row][col]) / \
                    (self.history[-1][TIMESTAMP] - t0)

        # We have more than 3 data points, calculate the slope of the linear regression.
        x_dataset = [ hist[TIMESTAMP]-t0 for hist in self.history ]
        y_dataset = [ hist[SAMPLE][row][col] for hist in self.history ]

        sum_x = sum_y = sum_xx = sum_yy = sum_xy = 0
        for x, y in zip(x_dataset, y_dataset):
            sum_x = sum_x + x
            sum_y = sum_y + y
            sum_xx = sum_xx + x*x
            sum_yy = sum_yy + y*y
            sum_xy = sum_xy + x*y

        det = sum_xx * n - sum_x * sum_x
        if det:
            return (sum_xy * n - sum_y * sum_x)/det
        return 0


    def check(self, user=None, nice=None, sys=None, all=None, nonnice=None, idle=None, io=None):
        """
        Checks the most recent sample against the given kwargs.
        """
        self.last_request_time = time.time()
        if self.poll_timer.active() or not self.history:
            # No data, conservatively assume 50% idle, 50% iowait, 50% proc cpu
            info = 0, 0, 0, 50, 50, 0, 0, 0, 0, 0, 50
        else:
            # take average row from latest sample
            info = self.history[-1][SAMPLE][AVG]

        if not self.poll_timer.active():
            self.poll_timer.start(0.3)

        if (user is not None and info[USER] >= user) or \
           (nice is not None and info[NICE] >= nice) or \
           (sys is not None and info[SYSTEM] >= sys) or \
           (all is not None and info[USER] + info[NICE] + info[SYSTEM] >= all) or \
           (nonnice is not None and info[USER] + info[SYSTEM] >= nonnice) or \
           (idle is not None and info[IDLE] < idle) or \
           (io is not None and info[IOWAIT] >= io):
            return True
        return False


    def next(self, policy):
        """
        Returns a base interval based on the given policy.  Caller may choose
        to multiply the suggested interval by some factor suitable for the
        task.

        policy value corresponds to config.scheduler.policy.
        """
        self.last_request_time = time.time()
        if not self.poll_timer.active():
            self.poll_timer.start(0.3)

        if self.cache and (not self.history or (self.history and self.history[-1][TIMESTAMP] <= self.cache[1])):
            # We haven't polled since the last next() call, so with no new
            # information, just return the last value.
            return self.cache[0]

        # Construct averaged sample over past 5 samples.
        samples = [hist[SAMPLE] for hist in self.history[-5:]]
        n = min(5, len(samples))
        window = [[sum(row)/n for row in zip(*rows)] for rows in zip(*samples)]

        # Whether or not we have enough samples to establish a trend.
        have_trend = len(self.history) > 1
        # Last wait time returned.
        last = wait = self.cache[0] if self.cache else 1

        # TODO: be smarter about IO wait.  If iowait is high but it's for a
        # block device that we're not interested in read/writing to, then
        # we can ignore it.  Also, we don't know how much of the IO is
        # caused by us, or some other process.  (Needs I/O accounting support
        # in 2.6.20)

        # TODO take slope of linear regression into account, basing the level
        # of throttling based on degree of slope.

        # XXX: the heuristics below are subject to refinement.

        if policy == 'polite':
            # Try to keep cpu usage of current process and iowait at around
            # 30%, even if other cores are idle.  The goal of this policy
            # is just to stay out of the way at all times.
            if not have_trend:
                # Should be a sane starting point for this policy
                wait = 0.05
            else:
                # TODO: check current cpu usage against self, and if other
                # processes are competing, back off even more.
                if window[AGGR][SELF] > 30 or window[AGGR][MAX_IO] > 30:
                    wait = max(last * 1.10, 0.01)
                elif window[AGGR][SELF] < 20 or (window[AGGR][MAX_IO] < 15 and window[AGGR][SELF] < 30):
                    wait = last * 0.95

        elif policy == 'aggressive':
            # As long as a core is idling, we go all out, except try to keep
            # IO to 85%.  If the most idle core is running hotter than 50%, we
            # back off to 50%.
            if not have_trend:
                wait = 0.005
            else:
                if window[AGGR][MAX_IO] > 85 or (window[AGGR][MIN_CPU] > 50 and window[AGGR][SELF] > 50):
                    wait = max(last * 1.10, 0.005)
                elif window[AGGR][MAX_IO] < 80 and window[AGGR][MIN_CPU] < 10:
                    wait = last * 0.95

        elif policy == 'greedy':
            # All your cpu are belong to me.
            wait = 0

        else:  # policy == 'balanced' or any other typo.
            # Try to keep cpu usage of current process at around 50% unless there
            # are other idle cores, then we let ourselves go up to 80%.  If
            # IO exceeds 60%, throttle back.
            if not have_trend:
                wait = 0.03
            else:
                if window[AGGR][SELF] > 80 or window[AGGR][MAX_IO] > 60 or \
                   (window[AGGR][SELF] > 50 and window[AVG][MIN_CPU] > 20):
                    wait = max(last * 1.10, 0.01)
                elif window[AGGR][SELF] < 50 or window[AGGR][MAX_IO] < 40 or \
                     (window[AGGR][SELF] < 80 and window[AVG][MIN_CPU] < 20):
                    wait = last * 0.95

        # We cap out a second.  Sleeping longer than this probably isn't going
        # to help matters.
        wait = min(wait, 1.0) if wait >= 0.0001 else 0.0
        log.debug('scheduler policy=%s window=%s  ->  wait=%.05f', policy, window[0] if window else None, wait)
        self.cache = (wait, self.last_request_time)
        return wait


scheduler = Scheduler('beacon-daemon')
check = scheduler.check
next = scheduler.next

if __name__ == '__main__':
    sched1 = Scheduler(os.getpid())
    sched2 = Scheduler(os.getpid())
    sched3 = Scheduler(os.getpid())

    def debug():
        print '-----------'
        print 'Polite:', sched1.next('polite')
        print 'Balanced:', sched2.next('balanced')
        print 'Aggressive:', sched3.next('aggressive')

    @kaa.coroutine()
    def add_load():
        x = 0
        for i in range(300000):
            yield kaa.NotFinished
        print "Done load generation"

    add_load()
    t = kaa.Timer(debug)
    t.start(0.3)
    kaa.main.run()
