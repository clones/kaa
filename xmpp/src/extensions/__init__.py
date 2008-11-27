import os
import kaa.utils

# load all extensions
for plugin in kaa.utils.get_plugins(os.path.dirname(__file__)):
    exec('import %s' % plugin)
