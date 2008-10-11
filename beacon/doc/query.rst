Database Query
==============

.. module:: query

Describe here how searching works in general.

.. autofunction:: beacon.query
.. autoclass:: beacon.Query


Methods
-------


This object feels like a list, you can iterate over the results,
access items based on position and get the length of the results.

.. automethod:: beacon.Query.get
.. automethod:: beacon.Query.__iter__
.. automethod:: beacon.Query.__getitem__
.. automethod:: beacon.Query.index
.. automethod:: beacon.Query.__len__

Describe monitoring here

.. automethod:: beacon.Query.monitor

Attributes
----------

Query has no public attributes. The monitor method should be a
property in the future.

Signals
-------

.. describe:: changed

   Emited when the query result changes. This only works when the
   query has monitoring turned on.

.. describe:: process

   This signal is emited during initial scanning. Since the Query is
   hidden by an InProgress object, it is not possible to connect to
   this signal anymore. It will be replaced in the future by the
   progress function of InProgress.

   **Arguments**: 
     - *pos* -- position
     - *max* -- maximum results

   *Deprectated*

.. describe:: up-to-date

   *Deprectated*
