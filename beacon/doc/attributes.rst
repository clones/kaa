Database Attributes
===================

Pre-Defined Item Attributes
---------------------------

The following attributes are available. If more are needed please call
`register_file_type_attrs` or `register_track_type_attrs`.

Directories (type = `dir`:)
 - `name`: str, searchable, inverted index: 'keywords'
 - `overlay`: bool, simple
 - `media`: int, searchable, indexed
 - `image`: int, simple
 - `mtime`: int, simple
 - `title`: unicode, simple
 - `artist`: unicode, simple
 - `album`: unicode, simple
 - `length`: float, simple (length in seconds of all items in that directory)

Items and Files (type = `file` and all media types)
 - `name`: str, searchable, inverted index: 'keywords'
 - `overlay`: bool, simple
 - `media`: int, searchable, indexed
 - `image`: int, simple
 - `mtime`: int, simple

Video Items (type = `video`)
 - `title`: unicode, searchable, ignore case, inverted index: 'keywords',
 - `width`: int, simple
 - `height`: int, simple
 - `length`: float, simple
 - `scheme`: str, simple
 - `description`: unicode, simple
 - `timestamp`: int, searchable

Audio Items (type = `audio`)
 - `title`: unicode, searchable, ignore case, inverted index: 'keywords'
 - `artist`: unicode, searchable, indexed, ignore case, inverted index: 'keywords'
 - `album`: unicode, searchable, ignore case, inverted index: 'keywords'
 - `genre`: unicode, searchable, indexed, ignore case
 - `samplerate`: int, simple
 - `length`: float, simple
 - `bitrate`: int, simple
 - `trackno`: int, simple
 - `userdate`: unicode, simple
 - `description`: unicode, simple
 - `timestamp`: int, searchable

Image Items (type = `image`)
 - `width`: int, searchable
 - `height`: int, searchable
 - `comment`: unicode, searchable, ignore case, inverted index: 'keywords'
 - `rotation`: int, simple
 - `author`: unicode, simple
 - `timestamp`: int, searchable

DVD Track Items (type = `dvd`)
 - `length`: float, simple
 - `audio`: list, simple
 - `chapters`: int, simple
 - `subtitles`: list, simple

VCD Track Items (type = `vcd`)
 - `audio`: list, simple

Audio CD Track Items (type = `cdda`)
 - `title`: unicode, searchable, inverted index: 'keywords'
 - `artist`: unicode, searchable, indexed, inverted index: 'keywords'


Additional Item Attributes
--------------------------

Besides the keys in the database an item has the following attributes
accessable with this function:

 - parent: parent or Item
 - media: Media object the item is on
 - thumbnail: Thumbnail object for the item or parent
 - image: image path for the item or parent
 - read_only: True if the item is on a read only media

If you access or store an attribute that starts with 'tmp:', the data
will only be stored inside the Item and not in the database. An Item
for the same file in the database will not have that attribute and it
will be lost when the application shuts down.


Thumbnails
----------

.. autoclass:: beacon.Thumbnail


Adding Application specific Attributes
--------------------------------------

Describe the basic usage how the db works here.

.. autofunction:: beacon.register_inverted_index
.. autofunction:: beacon.register_file_type_attrs
.. autofunction:: beacon.register_track_type_attrs


