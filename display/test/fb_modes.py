f = open('/etc/fb.modes')

PAL_768x576  = (768, 576, 768, 576, 0, 0, 0, 0, 38400, 20, 10, 30, 10, 10, 34, 19, 0)

sync_dict = { 'hsync high': 1,
              'vsync high': 2,
              'extsync true': 4,
              'csync high': 8,
              'bcast true': 16,
              'gsync high': 32
              }
name = ''
modes = {}
geometry = timings = []
sync = 0

for line in f.readlines():
    if line.find('#') != -1:
        line = line[:line.find('#')]
    line = line.strip()
    if not line:
        continue
    if line.startswith('mode '):
        name = line[5:].strip(' "\'')
    elif line.startswith('endmode'):
        if name and geometry and timings:
            print name, geometry, timings
            modes[name] = geometry[:-1] + [ 0,0,0,0] + timings + [ sync,0]
        else:
            print 'Invalid mode: %s' % name
        geometry = timings = []
        sync = 0
        
    elif line.startswith('geometry'):
        # xres, yres, vxres, vyres, depth
        geometry = [ int(g) for g in line.split(' ')[1:] ]
    elif line.startswith('timings'):
        # pixclock, left, right, upper, lower, hslen, vslen
        timings = [ int(t) for t in line.split(' ')[1:] ]
    elif line in sync_dict:
        print sync_dict[line]
    else:
        print 'unknwon line %s' % line
        geometry = timings = []
        sync = 0

print
for m in modes:
    print m, '=', modes[m]
