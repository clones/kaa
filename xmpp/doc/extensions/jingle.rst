Jingle
======

Client Plugin
-------------

.. autoclass:: xmpp.extensions.jingle.Responder
   :members:
   :undoc-members:


Remote Plugin
-------------

.. autoclass:: xmpp.extensions.jingle.Initiator
   :members:
   :undoc-members:


Session Object
--------------

.. autoclass:: xmpp.extensions.jingle.Session

   .. automethod:: xmpp.extensions.jingle.Session.initiate

   .. automethod:: xmpp.extensions.jingle.Session.accept

   .. automethod:: xmpp.extensions.jingle.Session.close

   .. attribute:: Session.state

      State of the Session. STATE_PENDING, STATE_ACTIVE or STATE_ENDED

   .. attribute:: Session.initiator

      XMPP JID of the session initiator
 
   .. attribute:: Session.sid

      Session Identifier

   .. attribute:: Session.content

      Content description of the session

   .. attribute:: Session.signals

      state-change(*sid*)
