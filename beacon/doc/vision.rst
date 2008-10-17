Vision
======

Note: The following text is copied from the beacon vision document
from Jason before beacon was written. The text may require some
updates.

Beacon's job is to act as an intermediary between the application and
the filesystem. It will offer an interface for applications to perform
queries on files. The result set can include any known data about the
files that match the query. For example, if one of the files in the
result set is an image, it could include the image's dimensions, color
space, thumbnail, EXIF data (in the case of a JPEG), precomputed
histogram, and so on.

Queries can include evaluations on any indexed field. One common query
would be "get a list of all files in directory X." Another possible
query is "get all music by Queen." Another slightly more complicated
query is "get all music by Moby, and all movies whose soundtrack has
Moby." Beacon is responsible for gathering all data necessary to
compute such queries and providing an appropriate interface to the
application. How Beacon computes such queries internally may vary, but
the API should not make this difference evident.

Another necessary feature of Beacon is notification of changes to the
query. If an application queries "all files in directory X," it should
be able to request notifications to changes, so that if, for example,
a file is added to directory X, the application is appropriately
notified. The actual behavior or performance may vary based on kernel
support or the nature of the query, but the API Beacon provides to the
application must support this functionality.

Common Use-Cases
----------------

The typical user will have a collection of media files, likely
organized in one or more hierarchies, on either a local filesystem, or
accessible via NFS or SMB. Users will also commonly have files stored
on removable media, such as USB drives, CDs, or DVDs.

Let's explore some scenarios of how the user will want to interact
with Beacon, and how we expect the interface might behave:

1. The user enters a directory of images on the local harddisk. The
   interface will display a grid of thumbnails in the current
   directory. The directory contents should be displayed in the
   interface as quickly as possible. Files are initially represented
   by a "Thumbnail loading" icon, and the icons are updated with the
   thumbnails as they are loaded. This process does not block the
   interface.

2. While the user is in the directory above, she copies a new image to
   that directory through some external method. The interface should
   quickly update to reflect the addition to the directory with the
   "Thumbnail loading" icon and subsequent thumbnail as described
   above. The user then deletes the image, and the interface quickly
   removes the image from the displayed list.

3. The user does a search for all music by Delerium. The interface
   displays a list of all songs matching this criteria.

4. On another computer, the user copies an MP3 file of a new song by
   Delerium to one of her music directories over her local
   network. The interface quickly updates the list from the above
   query to reflect the new song. (This assumes the MP3 has the proper
   ID3 tags.)

5. The user inserts a Delerium CD into the CD ROM drive. The list from
   the earlier query updates to show the songs from this CD. (This
   assumes the CD is listed in an accessible CDDB directory or that
   the CD has already been indexed.)

6. The user does a search for all images with the keyword
   vacation. The interface presents a list of thumbnails for images
   which the user has previously tagged with the vacation keyword.

7. The user inserts a DVD into the DVD drive which contains a number
   of images from her Hawaii vacation. This DVD was previously viewed
   by the user and she tagged the DVD with the vacation
   keyword. Shortly after the DVD is inserted, the list from the query
   in #6 automatically begins updating to show all images on the DVD.

8. The user does a search for all movies directed by Kevin Smith. The
   interface displays a list of movies on the harddisk matching this
   query, which are represented by images of their DVD covers. The
   list further displays all DVD movies by Kevin Smith that the user
   has played before. The interface will provide some appropriate
   indication that these DVDs are not present and must be inserted
   before they can be played. The user saves this query under the
   title Movies by Kevin Smith.

9. The user inserts a data DVD containing a number of MPEG4
   movies. The interface shows some indication that a DVD has been
   inserted. The user navigates to the DVD and it presents a list of
   video files (acquired through Beacon) on the root of the DVD with
   thumbnails. One of these movies is Dogma, by Kevin Smith. The user
   accesses the necessary interface to perform an online lookup by
   movie title, and selects the appropriate movie title/year for that
   video file. The user then navigates the interface to the saved
   query Movies by Kevin Smith and the interface shows the same list
   as in #8 with the addition of the recently added Dogma, which is
   now represented by an image of the Dogma DVD cover, rather than a
   thumbnail as before. The interface indicates that Dogma is stored
   on a DVD and is currently accessible.

The above use-cases illustrate some of the functionality the
application will require from Beacon. This list is not comprehensive,
and in many cases it may not be a very good idea for the interface to
behave exactly as described. However, Beacon should make any of the
above possible.


Feature Overview
----------------

From these use-cases we can derive a number of features we require Beacon to have:

1. List and index files in a requested directory. When Beacon indexes
   a file, it gathers any data it can about the file (metadata), which
   will depend on media type, and stores that metadata for future
   retrieval. Directories with thousands of files should be handled
   gracefully.

2. To ensure quick response, Beacon must index files, or load
   previously indexed metadata, asynchronously. When an application
   requests a directory list, Beacon will first obtain minimal data (a
   list of file names, sizes, and modification times). If the time for
   this operation so far is less than 0.1 seconds (the maximum time
   which the user perceives instant response), Beacon will begin
   loading previously indexed data until 0.1 seconds is reached. It
   will then return to the application the complete file list, and all
   metadata it managed to load before the 0.1 second timeout. For
   those files whose metadata was not loaded, it will load
   asynchronously and inform the application using some notification
   mechanism so that the interface may be updated as needed.

3. Beacon must be able to monitor directories for changes. A changed
   directory is one which contains an added file, a deleted file, or
   modified file that the application is not aware of. There must be
   an API to provide a means for the application to receive change
   notifications.

4. There must be some method to query all indexed files by certain
   metadata fields. Querying should behave as described in #1 and
   #2. In fact, even though they may be implemented differently within
   Beacon, the API to obtain a list of files in a directory and to
   query by metadata should be the same; they are both queries.

5. Similar to #2, Beacon should be able to monitor queries for
   changes. This is much more complicated than monitoring a single
   directory as in #2 because it requires monitoring all directories
   in the user's media repository and performing automatic indexing of
   new or changed files. Because this requires support from the kernel
   that may not be present on all systems , this live indexing should
   be optional. This means that Beacon should not rely on this
   functionality internally.

6. Beacon must be able to monitor removable media devices and
   determine when removable media has been added or removed. It must
   provide an API so that the application can be notified of such
   events.

7. Beacon must be able to index files on removable media, and
   distinguish between two files with the same name but on different
   media. For example, if the CDROM is mounted under /mnt/cdrom and
   there exists a file foo.jpg on two different CDs, Beacon should
   treat these as separate files, even though they have the same
   pathname /mnt/cdrom/foo.jpg.

8. Beacon must allow the application to store and retrieve metadata
   for a file. For example, in use-case #9, Beacon will retrieve
   certain metadata about the video such as resolution or length
   transparently to the application, but the application will retrieve
   the DVD image cover.
