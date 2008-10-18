Font Objects
============

.. autofunction:: imlib2.add_font_path
.. autofunction:: imlib2.load_font
.. autofunction:: imlib2.get_font_style_geometry

.. autoclass:: imlib2.Font

   The parameter fontdesc is the description of the font, in the form
   'Fontname/Size' or as a list/tuple in the form ('Fontname', size).
   Only TrueType fonts are supported, and the .ttf file must exist in
   a registered font path.  Font paths can be registered by calling
   Imlib2.add_font_path(). The color is a 3- or 4-tuple holding the
   red, green, blue, and alpha values of the color in which to render
   text with this font context.  If color is a 3-tuple, the implied
   alpha is 255.  If color is not specified, the default is fully
   opaque white.

Attributes
----------

.. attribute:: imlib2.Font.ascent

   the current font's ascent value in pixels.

.. attribute:: imlib2.Font.descent

   the current font's descent value in pixels.

.. attribute:: imlib2.Font.max_descent

   the current font's maximum descent extent.

.. attribute:: imlib2.Font.max_ascent

   the current font's maximum ascent extent.

.. attribute:: imlib2.Font.fontname

   name of the font (e.g. Vera)

.. attribute:: imlib2.Font.size

   font size

.. attribute:: imlib2.Font.style

   The style of the text. See set_style for details.


Member Functions
----------------

.. automethod:: imlib2.Font.get_text_size
.. automethod:: imlib2.Font.set_color
.. automethod:: imlib2.Font.set_size
.. automethod:: imlib2.Font.set_style
.. automethod:: imlib2.Font.get_style_geometry
