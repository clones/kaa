.. _query:

Query
=====

.. module:: query

FIXME: Describe here how searching works in general.

.. autofunction:: beacon.query


Methods
-------


This object feels like a list, you can iterate over the results,
access items based on position and get the length of the results.

.. automethod:: beacon.Query.get
.. automethod:: beacon.Query.__iter__
.. automethod:: beacon.Query.__getitem__
.. automethod:: beacon.Query.index
.. automethod:: beacon.Query.__len__

Monitoring
----------

FIXME: Describe monitoring here

.. automethod:: beacon.Query.monitor
.. autofunction:: beacon.monitor


Signal **changed**

   Emited when the query result changes.

Signal **process**

   This signal is emited during initial scanning.

   **Arguments**:
     - *pos* -- position
     - *max* -- maximum results

Signal **up-to-date**

   This signal is emited after initial scanning.

.. _filter:

Filter
------

FIXME: Describe filter here

.. autofunction:: beacon.register_filter
.. autofunction:: beacon.wrap
