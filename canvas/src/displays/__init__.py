from buffer import *

try:
    from x11 import *
except ImportError:
    pass

try:
    from fb import *
except ImportError:
    pass

try:
    from dfb import *
except ImportError:
    pass
