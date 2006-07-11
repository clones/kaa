import os
import re

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
