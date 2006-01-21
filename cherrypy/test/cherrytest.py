import kaa.cherrypy
import kaa.notifier
import kaa.notifier.thread
import threading

# cherrypy doc
# http://www.cherrypy.org/cherrypy-2.1.0/docs/book/chunk/index.html

# kid doc
# http://kid.lesscode.org/guide.html

# import a kid file with the header
import header

class Test:

    @kaa.cherrypy.expose()
    def index(self, pos):
        return 'test'

class Root:

    test = Test()
    
    @kaa.cherrypy.expose(template='test.kid', mainloop=False)
    def index(self, template):
        main = kaa.notifier.thread._thread_notifier_mainthread
        template.title = 'Test Kid Page'
        template.lines = ['qwe','asd','zxc']
        template.header = header.Template(text='index')
        # return some attributes as dict
        return { 'mainloop': main == threading.currentThread() } 
    
    @kaa.cherrypy.expose(template='test.kid')
    def main(self, template):
        main = kaa.notifier.thread._thread_notifier_mainthread
        template.title = 'Test Kid Page'
        template.lines = ['qwe','asd','zxc']
        template.header = header.Template(text='main')
        template.mainloop = main == threading.currentThread()
        # nothing needs to be returned, the logic is in the template
        
    @kaa.cherrypy.expose()
    def foo(self):
        return 'foo'

kaa.cherrypy.config.port = 8080
kaa.cherrypy.config.debug = True

kaa.cherrypy.start(Root)
kaa.notifier.loop()
