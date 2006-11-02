import os
import sys
import gettext
from kaa.config import Var, Group, Dict, List, Config

import backends

path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '../../../../share/locale'))
i18n = gettext.translation('kaa.popcorn', path, fallback=True).ugettext

config = Config(desc=i18n('Player configuration'), schema=[

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
