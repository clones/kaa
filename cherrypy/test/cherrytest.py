import os

import kaa.cherrypy
import kaa.notifier
import kaa.notifier.thread
import threading

# cherrypy doc
# http://www.cherrypy.org/cherrypy-2.1.0/docs/book/chunk/index.html

# kid doc
# http://kid.lesscode.org/guide.html

import kid

# enable importing kid files as python modules
kid.enable_import()

# import a kid file with the header
import header

class Test:

    @kaa.cherrypy.expose()
    def index(self):
        return 'test'

    @kaa.cherrypy.expose()
    def seven(self):
        return '7'

class Browse:

    @kaa.cherrypy.expose()
    def index(self, path='/'):
        return path

    @kaa.cherrypy.expose()
    def default(self, *args):
        return self.index('/' + '/'.join(args))
        
class Root:

    test = Test()
    browse = Browse()
    
    @kaa.cherrypy.expose(template='test.kid', mainloop=False)
    def index(self):
        main = kaa.notifier.thread._thread_notifier_mainthread
        return dict(title = 'Test Kid Page',
                    lines = os.listdir('/tmp/'),
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
kaa.cherrypy.config.root = '..'
kaa.cherrypy.config.static['/images'] = 'test'
kaa.cherrypy.config.static['/css'] = '/tmp'

kaa.cherrypy.start(Root)
kaa.notifier.loop()
