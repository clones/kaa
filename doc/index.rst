.. kaa documentation master file, created by sphinx-quickstart
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Kaa Media Repository
====================

The **Kaa Media Repository** is a set of python modules related to media.

Kaa modules are based on parts from Freevo and modules created for
MeBox. Kaa exists to encourage code sharing between these projects,
and to serve as an umbrella for several previously disparate
media-related modules in order to make them available from one
(unique) namespace.

Kaa provides a base module that implements the common features needed
for application development, such as mainloop management, timers,
signals, callbacks, file descriptor monitors, etc. Kaa's other modules
provide specific media-related functionality, such as retrieving
metadata on arbitrary media files (kaa.metadata, previously called
mmpython), Python wrappers for Imlib2, Xine, and Evas, and many other
high level APIs for easily creating applications that deal with video
and audio.

Kaa is named after the python character in the Jungle Book by Rudyard
Kipling.

Modules
-------

The maintainers for Kaa are Dirk Meyer (Dischi) and Jason Tackaberry
(Tack). Some projects have special maintainers and creators; we only
take care of the whole repository. If you have a module that fits into
Kaa, let us know. If you find a bug or have a patch, send a mail to
the freevo-devel mailing list.

Most documentation pages are not yet created. Feel free to add some
information about the module and how to use it.

kaa.base
^^^^^^^^

This module provides the base Kaa framework and is an implicit
dependency for all kaa modules. The kaa framework includes a mainloop
facility with an API for signals and callbacks, timers, process and
thread management, file descriptor monitoring (with INotify support),
inter-process communication, as well as a rich, practically magical
API for asynchronous programming

* See `kaa.base documentation <base/index.html>`_ for details.
* Download the latest `release of kaa.base
  <http://sourceforge.net/project/showfiles.php?group_id=46652&package_id=213183>`_
  from Sourceforge.
* Maintainer: Dirk Meyer, Jason Tackaberry
* License is LGPL.


kaa.beacon
^^^^^^^^^^

A virtual file system based on a sqlite database. It is a merge of the
current Freevo mediadb and vfs code. It is possible to get directory
listings or query database by keywords. Based on an kaa.metadata and
kaa.thumb, additional information about files / items can be
provided. The module is based on a kaa.base.rpc client server
architecture. It can also generate thumbnails for images and video
files and read embedded thumbnails in mp3 files. Optional a fuse
backend inside the client can be used to mount a query to a directory.

* See `kaa.beacon documentation <beacon/index.html>`_ for details.
* The module is not released yet
* Maintainer: Dirk Meyer
* The license for the beacon server is GPL, the client API is
  available under the LGPL.

kaa.candy
^^^^^^^^^

This module has no description yet

* Detailed documentation is unavailable.
* The module is not released yet
* Maintainer: Dirk Meyer
* License is LGPL

kaa.cherrypy
^^^^^^^^^^^^

This module has no description yet

* Detailed documentation is unavailable.
* The module is not released yet
* Maintainer: Dirk Meyer, Jason Tackaberry
* License is GPL

kaa.display
^^^^^^^^^^^

Low level support for various displays, such as X11 or
framebuffer. Provides X11Display and X11Window classes for managing
X11 windows, with optional support for Imlib2 (render Imlib2 images to
X11 windows) and pygame (render Imlib2 images to pygame surfaces).

* Detailed documentation is unavailable.
* The module is not released yet
* Maintainer: Jason Tackaberry
* License is LGPL

kaa.epg
^^^^^^^

An EPG module for python. It stores data using kaa.db and provides a
convenient interface to the different channels and classes. Data can
be added to the database with source modules; currently there is
support for XMLTV, Epgdata.com, and Schedules Direct. Although XMLTV
itself supports many data sources, native support for most popular
sources is desirable and contributions would be appreciated.

* Detailed documentation is unavailable.
* The module is not released yet
* Maintainer: Dirk Meyer, Jason Tackaberry
* License is LGPL

kaa.feedmanager
^^^^^^^^^^^^^^^

This module has no description yet

* Detailed documentation is unavailable.
* The module is not released yet
* Maintainer: Dirk Meyer
* License is GPL

kaa.imlib2
^^^^^^^^^^

This module has no description yet

* Detailed documentation is unavailable.
* Download the latest `release of kaa.imlib2
  <http://sourceforge.net/project/showfiles.php?group_id=46652&package_id=216046>`_
  from Sourceforge.
* Maintainer: Jason Tackaberry
* License is LGPL

kaa.metadata
^^^^^^^^^^^^

A powerful media metadata parser. It can extract metadata (such as id3
tags, for example) from a wide range of media files. Attributes like
codec, length, resolution, audio/video/subtitle tracks, and chapters
are also returned.

* See `kaa.metadata documentation <metadata/index.html>`_ for details.
* Download the latest `release of kaa.metadata
  <http://sourceforge.net/project/showfiles.php?group_id=46652&package_id=213173>`_
  from Sourceforge. The module is fully funtional; new parsers or
  enhancements to existing parsers are always needed.
* Maintainer: Dirk Meyer
* License is GPL.

kaa.mevas
^^^^^^^^^

This module has no description yet

* Detailed documentation is unavailable.
* The module is not released yet
* Maintainer: Jason Tackaberry
* License is LGPL


kaa.popcorn
^^^^^^^^^^^

This module has no description yet

* Detailed documentation is unavailable.
* The module is not released yet
* Maintainer: Dirk Meyer, Jason Tackaberry
* License is GPL


kaa.xine
^^^^^^^^

This module has no description yet

* Detailed documentation is unavailable.
* The module is not released yet
* Maintainer: Jason Tackaberry
* License is GPL

SVN Access
----------

Most of the modules in kaa are in heavy development and have no
releases yet. You can check out the current development tree of kaa
using subversion::

    svn co svn://svn.freevo.org/kaa/trunk kaa
