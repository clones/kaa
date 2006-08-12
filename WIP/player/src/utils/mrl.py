import os
import stat
import re

def parse_mrl(mrl):
    """
    Parses a mrl, returning a 2-tuple (scheme, path) where scheme is the mrl
    scheme such as file, dvd, fifo, udp, etc., and path is the whatever
    follows the mrl scheme.  If no mrl scheme is specified in 'mrl', it
    attempts to make an intelligent choice.
    """
    scheme, path = re.search("^(\w{,4}:)?(.*)", mrl).groups()
    if not scheme:
        scheme = "file"
        try:
            stat_info = os.stat(path)
        except OSError:
            return scheme, path

        if stat_info[stat.ST_MODE] & stat.S_IFIFO:
            scheme = "fifo"
        else:
            try:
                f = open(path)
            except (OSError, IOError):
                return scheme, path
            f.seek(32768, 0)
            b = f.read(60000)
            if b.find("UDF") != -1:
                b = f.read(550000)
                if b.find('OSTA UDF Compliant') != -1 or b.find("VIDEO_TS") != -1:
                    scheme = "dvd"
    else:
        scheme = scheme[:-1]
    return scheme, path
