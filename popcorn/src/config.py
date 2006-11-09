import os
import sys
import gettext
from kaa.config import Var, Group, Dict, List, Config

import backends

path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '../../../../share/locale'))
i18n = gettext.translation('kaa.popcorn', path, fallback=True).ugettext

config = Config(desc=i18n('Player configuration'), schema=[

    Var(name='widescreen', default='bars', type=('bars', 'zoom', 'scale'),
        desc=i18n("""
        How to handle 4:3 content on 16:9 screens. Possible values are
        bars:  add black bars on the left and on the right
        zoom:  zoom into the video, drop content on top and bottom
        scale: ignore aspect ratio and fill the screen
        """)),
        
    Var(name='prefered', default='xine', desc=i18n('prefered player')),
        
    # audio group
    Group(name='audio', desc=i18n('Audio settings'), schema=[
    Var(name='driver', type=('alsa', 'oss'), default='alsa',
        desc=i18n('audio driver (alsa or oss)')),
    Var(name='device', default='auto',
        desc=i18n('audio device')),
    Var(name='channels', type=('auto', 2, 4, 5, 6), default='auto',
        desc=i18n('number of channels (auto, 2, 4, 5 or 6)')),
    Var(name='spdif', default=False,
        desc=i18n('digital out'))
    ])
    ])

for n, c in backends.config:
    config.add_variable(n, c)
