import os
import sys

if not __file__.startswith(sys.argv[0]):
    print 'import'
    
    from manager import *

    for backend in os.listdir(os.path.dirname(__file__)):
        dirname = os.path.join(os.path.dirname(__file__), backend)
        if os.path.isdir(dirname):
            try:
                exec('import %s' % backend)
            except ImportError:
                pass
