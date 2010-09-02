Fonts
=====

.. autofunction:: imlib2.auto_set_font_path
.. autofunction:: imlib2.add_font_path
.. autofunction:: imlib2.load_font
.. autofunction:: imlib2.get_font_style_geometry

.. _textstyles:

Text Styles
-----------

These constants are used with :meth:`imlib2.Image.draw_text` and
:meth:`imlib2.Font.set_style`.

.. attribute:: imlib2.TEXT_STYLE_PLAIN

   No special styling.

.. attribute:: imlib2.TEXT_STYLE_SHADOW

   Draw text with a lower-right 1-pixel shadow.  The shadow color is specified
   by the *shadow* attribute.

.. attribute:: imlib2.TEXT_STYLE_SOFT_SHADOW

   Draw text with a lower-right blurred 5-pixel shadow, offset up and left by 1
   pixel.  The shadow color is specified by the *shadow* attribute.


.. attribute:: imlib2.TEXT_STYLE_FAR_SHADOW

   Draw text with a lower-right 2-pixel shadow.  The shadow color is specified
   by the *shadow* attribute.

.. attribute:: imlib2.TEXT_STYLE_FAR_SOFT_SHADOW

   Draw text with a lower-right blurred 5-pixel shadow.  The shadow color is
   specified by the *shadow* attribute.


.. attribute:: imlib2.TEXT_STYLE_OUTLINE

   Draw text with a 1-pixel outline.  The outline color is specified by the
   *outline* attribute.

.. attribute:: imlib2.TEXT_STYLE_OUTLINE_SHADOW

   Draw text with a 1-pixel outline and a lower-right 1-pixel shadow.  The
   outline and shadow and colors are specified by the *outline* and *shadow*
   attributes respectively.

.. attribute:: imlib2.TEXT_STYLE_SOFT_OUTLINE

   Draw text with a blurred 2-pixel outline.  The outline color is specified by
   the *outline* attribute.


.. attribute:: imlib2.TEXT_STYLE_OUTLINE_SOFT_SHADOW

   Draw text with a 1-pixel outline and a lower-right blurred 5-pixel shadow.
   The outline and shadow and colors are specified by the *outline* and
   *shadow* attributes respectively.


.. attribute:: imlib2.TEXT_STYLE_GLOW

   Draw text with a double outline.  The outer and inner outline colors are
   specified by the *glow* and *glow2* attributes respectively.


Font Objects
------------

.. kaaclass:: imlib2.Font
   :synopsis:

   .. automethods::
   .. autoproperties::
   .. autosignals::
