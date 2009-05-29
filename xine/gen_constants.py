#!/usr/bin/env python
#
# Reads xine.h and produces a list of constants
#
# This code is ugly.  Look away, it's hideous!
#
import re, sys

out = file("constants.py", "w")

defines = []
last = None
max_width = 0
for line in open("/opt/xine/current/include/xine.h").readlines():
    line = line.strip()
    if "VERSION" in line:
        continue

    m = re.match("^#define XINE_(\S+)\s+([^/]+)(.*)", line)
    if not m:
        continue

    var, val, comment = m.groups()
    val = val.replace("XINE_", "")

    while 1:
        m = re.search("'(.)'", val)
        if not m:
            break
        ch = m.group(1)
        val = val.replace("'%s'" % ch, str(ord(ch)))
    
    if len(var) > max_width:
        max_width = len(var)

    comment = re.sub("/\*|//|\*/", "", comment).strip()
    m = re.match("([^_]+)", var)
    if m:
        prefix = m.group(1)
    else:
        prefix = var

    if prefix != last:
        defines.append((None, None, None))
        last = prefix

    defines.append((var, val, comment))

for var, val, comment in defines:
    if var ==  None:
        out.write("\n")
        continue
    line = var.ljust(max_width+2)
    if comment:
        line += "= %s   # %s" % (val, comment)
    else:
        line += "= " + val
    out.write(line + "\n")
#
