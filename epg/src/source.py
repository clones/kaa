import os

sources = {}

for f in os.listdir(os.path.dirname(__file__)):
    if not f.startswith('source_') or not f.endswith('.py'):
        continue
    try:
        exec('import %s as s' % f[:-3])
    except ImportError:
        continue
    sources[f[7:-3]] = s
