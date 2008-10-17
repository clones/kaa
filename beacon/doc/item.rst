Beacon Item
===========

.. module:: item

Items are returned by beacon queries and represent one result
entry. You should not create an Item yourself. Beacon provides two
query functions. The first one is `kaa.beacon.query` which returns a
Query object and the second one is `kaa.beacon.get` to get the item
for a specific filename.

There are currently two kinds of Items. The generic Item class and a
File class inheriting from Item.

.. autofunction:: beacon.get

Methods
-------

An Item uses a dict-like interface to get and set values. If the key
starts with `tmp:` the value is stored temporary in the Item and is
not stored in the database. A second Item for the same database entry
does not have this attribute and it is lost when the Item is
destroyed. See :ref:`attributes` for a list of attributes in the
database.

.. automethod:: beacon.Item.get
.. automethod:: beacon.Item.__getitem__
.. automethod:: beacon.Item.has_key
.. automethod:: beacon.Item.keys
.. automethod:: beacon.Item.__setitem__

An Item also provides an interface to access children like files in a
directory, delete an Item from the database and initiate an Item to be
scanned.

.. automethod:: beacon.Item.list
.. automethod:: beacon.File.list
.. automethod:: beacon.Item.delete
.. automethod:: beacon.Item.scan

Attributes
----------

Besides the attributes in the database an Item also has some Python
attributes. These attributes are always set no matter of the file
behind it is already scanned or not.

.. attribute:: beacon.Item.url

   URL for the Item. This includes a prefix like file\://, dvd\:// or
   http\://

.. attribute:: beacon.Item.filename

   Full path of the file if the Item represents a file or
   directory. For Item that are no File this attribute is an empty
   string.

.. autoattribute:: beacon.Item.isdir
.. autoattribute:: beacon.Item.isfile
.. autoattribute:: beacon.Item.thumbnail
.. autoattribute:: beacon.Item.scanned
.. autoattribute:: beacon.Item.ancestors
