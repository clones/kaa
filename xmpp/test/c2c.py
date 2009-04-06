import logging
import os
import sys

import kaa
import kaa.utils
import kaa.xmpp

# XXX Please add username, servername, and password
username = ''
servername = ''
password = ''
# XXX Toggle between link-local and server based test
link_local = False

logging.getLogger('xmpp').setLevel(logging.DEBUG)

class MyXEP0030(kaa.xmpp.extensions.disco.Client):

    @kaa.xmpp.iq(xmlns=kaa.xmpp.extensions.disco.NS_DISCO_INFO)
    def _handle_query(self, jid, stanza, const, stream):
        print 'I got a disco#query'
        return super(MyXEP0030, self)._handle_query(jid, stanza, const, stream)

class Foo(object):

    @kaa.xmpp.iq(xmlns='test')
    def foo(self, jid, node, const, stream):
        print 'c2:     got foo from peer'
        print 'c2:     stream properties:', stream.properties
        return kaa.xmpp.Result('bar', xmlns='test')

class Credentials(kaa.xmpp.extensions.xtls.Credentials):

    def srp_supported(self):
        return True

    def srp_get_password(self, remote):
        return '1234'

MyXEP0030.install()
Credentials.install()

@kaa.coroutine()
def discover(node):
    try:
        print 'c1: found node:', node.jid
        yield node.disco.query()
        print 'c1: supported extensions:', ' '.join(node.extensions)
        if not node.stream.properties.get('e2e-stream'):
            if 'jingle-streams' in node.extensions:
                print 'open secure connection'
                yield node.get_extension('jingle-streams').connect()
            else:
                print 'secure connection not supported'
        print 'c1: send foo iq'
        answer = yield node.iqset('foo', xmlns='test')
        print 'c1: answer is', answer
        print
    except Exception, e:
        print e
    print 'shut down'
    sys.exit(0)

def roster(jid, status, node, client):
    # Roster callback, needs some cleanup. See roster.py for details
    if client.jid == jid:
        # FIXME: do not notify for ourself
        return
    if status:
        discover(client.get_node(jid))


def message(entity, msg):
    """
    Generic <message> callback
    """
    print 'unknown message', msg


@kaa.coroutine()
def main():
    # create first client
    c = kaa.xmpp.Client('Client1', '%s@%s/client1' % (username, servername))
    c.signals['message'].connect(message)
    c.signals['presence'].connect(discover)
    if link_local:
        c.activate_extension('link-local', announce=True)
    else:
        c.activate_extension('jingle-streams')
        yield c.connect(password)
        # FIXME: update roster to hook into c.signals['presence'] and to
        # register automaticly
        c.roster.signals['presence'].connect(roster, c)
        c.roster.register()

    # create second client
    c = kaa.xmpp.Client('Client2', '%s@%s/client2' % (username, servername))
    c.xmpp_connect(Foo())
    if link_local:
        c.activate_extension('link-local').announce()
    else:
        c.activate_extension('jingle-streams')
        yield c.connect(password)
        # FIXME: update roster to hook into c.signals['presence'] and to
        # register automaticly
        c.roster.register()


# some setup stuff, problem with kaa and dbus, just ignore it
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop( set_as_default=True )
kaa.main.select_notifier('generic')
kaa.gobject_set_threaded()

main()
kaa.main.run()
