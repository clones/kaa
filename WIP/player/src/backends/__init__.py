import os

for backend in os.listdir(os.path.dirname(__file__)):
    dirname = os.path.join(os.path.dirname(__file__), backend)
    if os.path.isdir(dirname):
        print 'import', backend
        try:
            exec('import %s' % backend)
        except ImportError:
            pass
