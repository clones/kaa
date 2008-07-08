import kaa
import kaa.candy
import kaa.input, kaa.input.stdin
import time, random, sys

c = kaa.candy.X11Canvas((640, 480), use_gl=0)
i = kaa.candy.Image("data/background.jpg", width='100%', height='100%')
c.add_child(i)
#c1 = kaa.candy.Container()
#c.add_child(c1)

c1 = kaa.candy.Container(debug = True, pos=('10%', 100), size=("300", "auto"), name='c1')
#c1['padding'] = 50, 50, 50, 50
c1['padding'] = 10, 10, 10, 10
#c1['padding'] = 100, 100, 100, 100
c.add_child(c1)


cc=kaa.candy.Container(top='20%', left='20%')
vid = kaa.candy.Image('data/video.png', size=('100%', '100%'), opacity=0.5, passive=True)
#vid['padding'] = 50, 0, 50, 35
#print "*****", vid.get_computed_inner_position()
cc.add_child(vid)
c.add_child(cc)
r = kaa.candy.Rectangle(size = ('60%', '30%'), opacity=0.2)
cc.add_child(r)

r2 = kaa.candy.Rectangle(size = ('100%', '50'), color="#f00", passive=True)
r2['padding'] = '5%', '5%', '5%', '5%'
c1.add_child(r2)




c2 = kaa.candy.Container(debug=True, name='c2', passive=False)
c2['padding'] = 20, 20, 20, 20
c2['pos'] = 50, 50
c2['size'] = 100, 200
c1.add_child(c2)

r3 = kaa.candy.Rectangle(color=(0, 255, 0))
r3['size'] = '50%', '50%'
r3['opacity'] = 0.5
c2.add_child(r3)

o=1
frames=0
t0=None
def anim():
    global o, t0, frames
    cx=c1
    if not t0:
        t0=time.time()
    t1=time.time()
    if t1-t0 > 1:
        sys.stderr.write("FPS: %f\n" % (frames/(t1-t0)))
        t0=t1
        frames=0

    p = cx['padding']
    width = cx.get_computed_inner_size()[0]
    if width < 50:
        o=-1
    elif width > 275:
        o=1
    cx['padding'] = p[0]+o, p[1]+o, p[2]+o, p[3]+o
    frames+=1
    #print '------------------------------------------------------', p, width, cx['padding']

def rs():
    #print r.get_computed_size()
    #c1['size'] = '400', 'auto'
    r2['passive'] = False
    
    r['size'] = ('70%', '40%')
    #c1['padding'] = 20, 20, 20, 20
    #r['size'] = '100%', 100
    #print r2._get_computed_padding()
    #r['opacity'] = 0.5
    #print r.get_computed_size()

kaa.notifier.Timer(anim).start(0)
#kaa.signals['stdin_key_press_event'].connect(lambda dummy: anim())
kaa.notifier.OneShotTimer(rs).start(1.5)

if 0:
    rects=[]
    random_colors = [ (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) for x in range(500*2) ]
    random_pos = [ (random.randint(0, 600), random.randint(0, 400)) for x in range(500*2) ]
    print "---------------------------------------"
    t0=time.time()
    for i in range(250):
        r=kaa.candy.Rectangle(size=(150,100), color=random_colors.pop(), opacity=0.3, pos = random_pos.pop())
        c1.add_child(r)
        rects.append(r)
    print "---------------------------------------"
    print "Made 250 objects", time.time()-t0


    t0 = time.time()
    frames = 0
    def v():
        #cont['visible'] = True
        #cont['color'] = (100, 255, 255)
        #cont['opacity'] = 0.6
        global frames
        if c1['opacity'] <= 0:
        #if rects[0]['opacity'] <= 0:
            took = time.time()-t0
            print "--", frames, took, frames/took
            return False

        x, y = c1['pos'][:2]
        o=c1['opacity']
        c1.move((x-2, y-2, None, None, None, None))
        c1['opacity'] = o-0.01
        print c1['opacity']
#    for r in rects:
#        x, y = r['pos']
#        o = r['opacity']
#        r.move((x-2, y-2))
#        r['opacity'] = o-0.0078
        frames += 1

    kaa.notifier.Timer(v).start(0)
#kaa.notifier.OneShotTimer(v).start(2)
#profile.run('kaa.main()')
kaa.main()
