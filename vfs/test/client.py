import kaa.vfs.client
import kaa

def foo(self):
    print 'done 2'
    
c = kaa.vfs.client.Client()
l = c.listdir('/home/dmeyer/video')
print l
for i in l.items:
    print i
#l.update(__ipc_async = foo)
print 'done'
print l
kaa.main()
