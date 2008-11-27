In-band Bytestreams (IBB)
=========================

`XEP-0047 In-Band Bytestreams <http://www.xmpp.org/extensions/xep-0047.html>`_

A client must activate the 'ibb' extension to make In-Band Bytestreams
possible. A different protocol must be used to exchange the sid of the
stream. One side has to call 'open', the other side 'listen'. It will
return a kaa.Socket on both ends. Closing the socket will close the
bytestream.

Client Plugin
-------------

.. autoclass:: xmpp.extensions.ibb.Client
   :members:


Remote Plugin
-------------

.. autoclass:: xmpp.extensions.ibb.IBB
   :members: listen, jingle_transport, jingle_listen

Signals
  **closed** (*sid*)
    This signal is emited when an IBB stream is closed. Note: right now
    the signal has no arguments, but it will get one.

    **Arguments**: 
      - *sid* -- Stream SID


Stream Object
-------------

.. autoclass:: xmpp.extensions.ibb.IBBSocket
   :members: read, send, close
