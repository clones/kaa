import kaa, kaa.display, kaa.evas
import time, random, sys

random_colors = [ (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) for x in range(500*2) ]
random_pos = [ (random.randint(0, 600), random.randint(0, 400)) for x in range(500*2) ]

def make_rect(e):
    r = e.object_rectangle_add()
    r.color_set(*random_colors.pop() + (150,))
    r.resize((150, 100))
    r.move(random_pos.pop())
    r.show()
    return r

def make_text(e, label):
    t = e.object_text_add(("arial", 14), label)
    t.color_set(*random_colors.pop() + (150,))
    t.move(random_pos.pop())
    t.show()
    return t

win = kaa.display.EvasX11Window(size=(640, 480), gl = False)
e = win.get_evas()

kaa.evas.benchmark_reset()
tt=t0=time.time()
bg = e.object_image_add("data/background.jpg")
bg.show()
print "- bg image:", time.time()-t0

rects=[]
t0=time.time()
for i in range(250):
    r=make_rect(e)
    rects.append(r)
print "- 250 rects:", time.time()-t0

text=[]
t0=time.time()
for i in range(250):
    t=make_text(e, "%d" % i)
    rects.append(t)
print "- 250 texts:", time.time()-t0



t0=time.time()
e.render()
print "- render:", time.time()-t0
print "- ALL:", time.time()-tt, kaa.evas.benchmark_get()
win.show()

frames=0
def update():
    tt=t0=time.time()
    tot=0
    for o in rects + text:
        tx=time.time()
        a = o.color_get()[3]
        if a-5<0:
            tot=time.time()-ts
            etot=kaa.evas.benchmark_get()
            print "- Animation took:", tot, etot, "OVERHEAD=", (tot/etot), " fps:", frames/(time.time()-ts)
            return False
        p = o.geometry_get()[0]
        o.color_set(a=a-2)
        o.move((p[0]-2, p[1]-2))
        tot+=time.time()-tx

    #print " - move/fade all:", time.time()-t0
    #print " - gets:", tot
    t0=time.time()
    e.render()
    #print " - render:", time.time()-t0
    global frames
    frames+=1

def start():
    global ts
    ts=time.time()
    kaa.evas.benchmark_reset()
    kaa.notifier.Timer(update).start(0)
kaa.notifier.OneShotTimer(start).start(2)
kaa.main()
