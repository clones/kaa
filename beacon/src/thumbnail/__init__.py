import os
from thumbnail import Thumbnail, NORMAL, LARGE, connect, \
     PRIORITY_HIGH, PRIORITY_NORMAL, PRIORITY_LOW

support_video = False
for path in os.environ.get('PATH').split(':'):
    if os.path.isfile(path + '/mplayer'):
        support_video = True
        
