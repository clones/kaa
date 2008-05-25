import os

import kaa
import kaa.cherrypy
import kaa.notifier.thread
import threading

# cherrypy doc
# http://www.cherrypy.org/wiki/TableOfContents

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

# http://www.cherrypy.org/wiki/StaticContent
kaa.cherrypy.mount(Root, '/', {
    # Base directory for all static dirs.
    '/': {
        'tools.staticdir.root': '/tmp'
    },

    # Request http://server:8080/css/foo.css loads /tmp/styles/foo.css
    '/css': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': 'styles'
    },

    '/images': {
        'tools.staticdir.on': True,
        'tools.staticdir.dir': os.path.dirname(os.path.realpath(__file__))
    },

})

kaa.cherrypy.start({
    'server.socket_port': 8080
})

kaa.main.run()
