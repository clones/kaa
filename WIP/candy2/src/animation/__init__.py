# FIXME: This submodule needs a huge cleanup

import core
import kaa.candy

def get(name):
    return kaa.candy.xmlparser.get_class('animation', name)
