__all__ = [ 'start' ]

import socket

import cherrypy._cpwsgiserver
import cherrypy._cpwsgi
import cherrypy._cpserver

import kaa.notifier

class WSGIServer(cherrypy._cpwsgi.WSGIServer):

    def start(self):
        """
        Start the server with help of the notifier main loop.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                                    socket.IPPROTO_TCP)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.bind_addr)
        self.socket.listen(5)
        
        # Create worker threads
        for i in xrange(self.numthreads):
            self._workerThreads.append(cherrypy._cpwsgiserver.WorkerThread(self))
        for worker in self._workerThreads:
            worker.start()
        for worker in self._workerThreads:
            while not worker.ready:
                time.sleep(.1)
        
        self.ready = True
        self.accept_disp = kaa.notifier.SocketDispatcher(self.accept)
        self.accept_disp.register(self.socket)


    def accept(self):
        s, addr = self.socket.accept()
        if hasattr(s, 'setblocking'):
            s.setblocking(1)
        request = cherrypy._cpwsgiserver.HTTPRequest(s, addr, self)
        self.requests.put(request)
        return True


    def stop(self):
        self.accept_disp.unregister()
        cherrypy._cpwsgi.WSGIServer.stop(self)
        

class Server(cherrypy._cpserver.Server):

    def start_http_server(self, blocking=True):
        """Start the requested HTTP server."""
        if self.httpserver is not None:
            msg = ("You seem to have an HTTP server still running."
                   "Please call server.stop_http_server() "
                   "before continuing.")
            warnings.warn(msg)
        
        if self.httpserverclass is None:
            return
        
        if cherrypy.config.get('server.socketPort'):
            host = cherrypy.config.get('server.socketHost')
            port = cherrypy.config.get('server.socketPort')
            
            cherrypy._cpserver.wait_for_free_port(host, port)
            
            if not host:
                host = 'localhost'
            onWhat = "http://%s:%s/" % (host, port)
        else:
            onWhat = "socket file: %s" % cherrypy.config.get('server.socketFile')
        
        # Instantiate the server.
        self.httpserver = self.httpserverclass()

        self.httpserver.start()
        cherrypy.log("11 Serving HTTP on %s" % onWhat, 'HTTP')
    

def start(Root, *args, **kwargs):
    cherrypy.root = Root(*args, **kwargs)
    cherrypy.config.update({'autoreload.on': False})
    cherrypy.server = Server()
    cherrypy.server.start(True, WSGIServer)
    kaa.notifier.signals['shutdown'].connect(cherrypy.server.stop)


