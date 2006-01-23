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

class TemplatePath:
    def __init__(self, engine, path, suffix_list):
        pass
    
class Root:

    test = Test()

    @kaa.cherrypy.expose(template='test.kid', mainloop=False)
    def index(self):
        main = kaa.notifier.thread._thread_notifier_mainthread
        return dict(title = 'Test Kid Page',
                    lines = ['qwe','asd','zxc'],
                    header = header.Template(text='index'),
                    mainloop = main == threading.currentThread())
    

    @kaa.cherrypy.expose(template='test.kid')
    def main(self):
        main = kaa.notifier.thread._thread_notifier_mainthread
        return dict(title = 'Test Kid Page',
                    lines = ['qwe','asd','zxc'],
                    header = header.Template(text='index'),
                    mainloop = main == threading.currentThread())
        

    @kaa.cherrypy.expose(template='cheetah.html', engine='cheetah')
    def cheetah(self):
        return dict(lines = ['qwe','asd','zxc'])
        

    @kaa.cherrypy.expose()
    def foo(self):
        return 'foo'

kaa.cherrypy.config.port = 8080
kaa.cherrypy.config.debug = True

kaa.cherrypy.start(Root)
kaa.notifier.loop()
