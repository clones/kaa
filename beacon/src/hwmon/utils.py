import os
import re

FILENAME_REGEXP = re.compile("^(.*?)_(.)(.*)$")

def fstab():
    if not os.path.isfile('/etc/fstab'):
        return []
    result = []
    regexp = re.compile('([^ \t]*)[ \t]*([^ \t]*)[ \t]*([^ \t]*)[ \t]*([^ \t]*)')
    fd = open('/etc/fstab')
    for line in fd.readlines():
        if line.find('#') >= 0:
            line = line[:line.find('#')]
        line = line.strip()
        if not line:
            continue
        if not regexp.match(line):
            continue
        device, mountpoint, type, options = regexp.match(line).groups()
        device = os.path.realpath(device)
        result.append((device, mountpoint, type, options))
    fd.close()
    return result


def get_title(name):
    """
    Convert name into a nice title
    """
    if len(name) < 2:
        return name

    if name.find('.') > 0 and not name.endswith('.'):
        name = name[:name.rfind('.')]

    # TODO: take more hints
    if name.upper() == name.lower():
        name = name.lower()
    name = name[0].upper() + name[1:]
    while True:
        m = FILENAME_REGEXP.match(name)
        if not m:
            break
        name = m.group(1) + ' ' + m.group(2).upper() + m.group(3)
    if name.endswith('_'):
        name = name[:-1]
    return name
