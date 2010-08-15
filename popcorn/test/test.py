import sys
import logging
import time
import os

import kaa.input.stdin
from kaa.popcorn.backends import manager
import kaa.popcorn

TESTCASES = []
FILES = sys.argv[1:]

#logging.getLogger('popcorn').setLevel(logging.DEBUG)
#logging.getLogger('base').setLevel(logging.DEBUG)

# TODO: timeout, seek, stream properties, methods called in wrong states,
# stop(), pause(), and resume() as singletons, chained seek()

def testcase(func):
    TESTCASES.append(func)
    return func

@testcase
@kaa.coroutine()
def open_normal():
    """
    Straightforward open yield.
    """
    p = kaa.popcorn.Player()
    yield p.open(FILES[0])
    assert(p.state == kaa.popcorn.STATE_OPEN)
    yield p


@testcase
@kaa.coroutine()
def open_abort_with_stop():
    """
    Open but don't yield, then yield stop.  Tests player's ability to abort an
    open.
    """
    p = kaa.popcorn.Player()
    open_ip = p.open(FILES[0])
    stop_ip = p.stop()
    try:
        yield open_ip
    except kaa.popcorn.PlayerAbortedError, e:
        # open() indicates as aborted, good.
        pass
    else:
        raise RuntimeError('open() yield following stop() did not throw PlayerAbortedError as expected')
    yield stop_ip
    assert(p.stopped)


@testcase
@kaa.coroutine()
def open_twice():
    """
    Open but don't yield, then yield a new open.  Similar to open_abort_with_stop
    but tests internal aborting.
    """
    p = kaa.popcorn.Player()
    p.open(FILES[0])
    yield p.open(FILES[1])
    assert(FILES[1] in p.stream.uri)
    assert(p.opened)

@testcase
@kaa.coroutine()
def play_premature():
    p = kaa.popcorn.Player()
    p.open(FILES[0])
    try:
        yield p.play()
    except kaa.popcorn.PlayerError, e:
        assert('STATE_OPENING is not' in e.message)
    else:
        raise RuntimeError('play() was improperly allowed before open() finished')

@testcase
@kaa.coroutine()
def play_normal():
    p = yield open_normal()
    yield p.play()
    assert(p.playing)
    pos = p.stream.position
    print '\tplaying for 2 seconds ...', pos
    yield kaa.delay(2)
    print '\tback ...', p.stream.position
    assert(p.stream.position > pos)
    yield p.stop()
    assert(p.stopped)


@testcase
@kaa.coroutine()
def play_induce_backend_failure():
    """
    Kill the backend child while it's playing and make sure an exception
    is thrown to the player InProgress.
    """
    p = yield open_normal()
    yield p.play()

    def kill():
        print '\tkilling backend with pid %d' % p._backend._child.pid
        os.kill(p._backend._child.pid, 15)
    kaa.OneShotTimer(kill).start(1)

    try:
        yield kaa.inprogress(p).timeout(5)
    except kaa.popcorn.PlayerError, e:
        # FIXME: determine if it failed for the right reason.
        pass
    else:
        raise SystemError('Simulated backend failure did not raise PlayerError as expected')
        

@kaa.coroutine()
def go():
    for test in TESTCASES:
        #if test.func_name != 'play_induce_backend_failure': continue
        print '-- Test case: %s' % test.func_name
        yield test()
        
    print '-- All test cases completed.'
    sys.exit(0)

if len(FILES) < 2:
    print 'Usage: %s file1 file2' % sys.argv[0]
    sys.exit(0)

print 'Available backends:', manager.get_all_players()
go()
kaa.main.run()
