Image Objects
=============

Creating image objects
----------------------

The following functions create Image objects:

.. autofunction:: imlib2.open
.. autofunction:: imlib2.open_without_cache
.. autofunction:: imlib2.open_from_memory
.. autofunction:: imlib2.new
.. autoclass:: imlib2.Image


Attributes
----------

.. attribute:: size

   tuple containing the width and height of the image

.. attribute:: width

   width of the image

.. attribute:: height

   height of the image

.. attribute:: format

   format of the image if loaded from file (e.g. PNG, JPEG)

.. attribute:: rowstride

   number of bytes per row of pixels

.. attribute:: has_alpha

   True if the image has an alpha channel, False otherwise

.. attribute:: filename

   filename if loaded from file

Drawing on Images
-----------------

.. automethod:: imlib2.Image.blend
.. automethod:: imlib2.Image.clear
.. automethod:: imlib2.Image.draw_rectangle
.. automethod:: imlib2.Image.draw_ellipse
.. automethod:: imlib2.Image.draw_mask
.. automethod:: imlib2.Image.draw_text
.. automethod:: imlib2.Image.set_font
.. automethod:: imlib2.Image.get_font
.. automethod:: imlib2.Image.get_pixel
.. automethod:: imlib2.Image.thumbnail
.. automethod:: imlib2.Image.copy_rect
.. automethod:: imlib2.Image.get_raw_data
.. automethod:: imlib2.Image.put_back_raw_data
.. automethod:: imlib2.Image.set_alpha

Effects
-------

.. automethod:: imlib2.Image.orientate
.. automethod:: imlib2.Image.flip_horizontal
.. automethod:: imlib2.Image.flip_vertical
.. automethod:: imlib2.Image.flip_diagonal
.. automethod:: imlib2.Image.blur
.. automethod:: imlib2.Image.sharpen

Create modified Images
----------------------

The following member functions will not alter the Image and return a
new Image instead.

.. automethod:: imlib2.Image.copy
.. automethod:: imlib2.Image.scale
.. automethod:: imlib2.Image.scale_preserve_aspect
.. automethod:: imlib2.Image.crop
.. automethod:: imlib2.Image.rotate
.. automethod:: imlib2.Image.as_gdk_pixbuf
.. automethod:: imlib2.Image.save
