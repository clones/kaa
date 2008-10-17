Database Manipulation
=====================

.. autofunction:: beacon.get_db_info

Creating Items
--------------

FIXME: Add description

.. autofunction:: beacon.add_item

.. _define-attributes:

Adding Application Specific Attributes
--------------------------------------

FIXME: Describe the basic usage how the db works here.

.. autofunction:: beacon.register_inverted_index
.. autofunction:: beacon.register_file_type_attrs
.. autofunction:: beacon.register_track_type_attrs

.. autoclass:: beacon.QExpr
.. attribute:: beacon.ATTR_SIMPLE
.. attribute:: beacon.ATTR_SEARCHABLE
.. attribute:: beacon.ATTR_IGNORE_CASE
.. attribute:: beacon.ATTR_INDEXED
.. attribute:: beacon.ATTR_INDEXED_IGNORE_CASE
.. attribute:: beacon.ATTR_INVERTED_INDEX
