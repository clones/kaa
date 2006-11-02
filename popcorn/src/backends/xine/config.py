import os
import sys
import gettext
from kaa.config import Var, Group, Dict, List

path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '../../../../share/locale'))
i18n = gettext.translation('kaa.popcorn', path, fallback=True).ugettext

config = Group(desc=i18n('xine configuration'), schema=[
    Var(name='activate', default=True, desc=i18n('activate backend'))
    ])
