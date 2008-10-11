Beacon Item
===========

.. module:: item
.. autofunction:: beacon.get

Items are returned by beacon queries and represent one result
entry. You should not create an Item yourself. There are currently two
kinds of Items. The generic Item class and a File class inheriting
from Item.

.. autoclass:: beacon.Item
.. autoclass:: beacon.File

Methods
-------

.. automethod:: beacon.Item.get
.. automethod:: beacon.Item.__getitem__
.. automethod:: beacon.Item.has_key
.. automethod:: beacon.Item.keys
.. automethod:: beacon.Item.__setitem__
.. automethod:: beacon.Item.list
.. automethod:: beacon.File.list
.. automethod:: beacon.Item.delete
.. automethod:: beacon.Item.scan

Attributes
----------

.. attribute:: beacon.Item.url

   URL for the Item. This includes a prefix like file, dvd or http

.. attribute:: beacon.Item.filename

   Full path of the file if the Item represents a file or directory

.. autoattribute:: beacon.Item.isdir
.. autoattribute:: beacon.Item.isfile
.. autoattribute:: beacon.Item.thumbnail
.. autoattribute:: beacon.Item.scanned
.. autoattribute:: beacon.Item.ancestors

Signals
-------

Item has no signals to connect to

