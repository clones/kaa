import os
import sys
import gc

# insert kaa path information
__site__ = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../../..'))
if not __site__ in sys.path:
    sys.path.insert(0, __site__)

import kaa
import kaa.shm

from child import XinePlayerChild as Xine

player = Xine(sys.argv[1], sys.argv[2])
kaa.main.run()

# Remove shared memory.  We don't detach right away, because the vo
# thread might still be running, and it will crash if it tries to write
# to that memory.
if player._osd_shmem:
    kaa.shm.remove_memory(player._osd_shmem.shmid)
if player._frame_shmem:
    kaa.shm.remove_memory(player._frame_shmem.shmid)

# Force garbage collection for testing.
del player
gc.collect()

sys.exit(0)
