import os

for plugin in os.listdir(os.path.dirname(__file__)):
    if plugin.endswith('.py') and not plugin == '__init__.py':
        exec('import %s' % os.path.splitext(plugin)[0])
    
