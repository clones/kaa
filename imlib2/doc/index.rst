kaa.imlib2 --- Image Processing Library
=======================================

What is kaa.imlib2?
-------------------

kaa.imlib2 provides thread-safe Python bindings for Imlib2, a featureful and
efficient image processing library, which produces high quality, anti-aliased
output.

Although kaa.imlib2 does not yet provide complete coverage of the Imlib2
library, most common functions are implemented.  It also implements some custom
functionality not found in Imlib2, such as :meth:`Image.draw_mask
<imlib2.Image.draw_mask>`.

In addition to Imlib2 itself, kaa.imlib2, as with all kaa modules, requires
`kaa.base <http://doc.freevo.org/api/kaa/base/>`_.


Where do I get kaa.imlib2?
--------------------------

If you haven't already, you must install `kaa.base
<http://doc.freevo.org/api/kaa/base/#where-do-i-get-kaa-base>`_.

Source packages for *kaa.imlib2* releases are `available on SourceForge
<http://sourceforge.net/projects/freevo/files/kaa-imlib2/>`_.

Your distribution might already have *kaa.imlib2* included in its standard
repositories::

    # For Ubuntu and Debian
    sudo apt-get install python-kaa-imlib2

    # For Fedora
    yum install python-kaa-imlib2


If you have *setuptools* installed (package named ``python-setuptools`` on
Ubuntu and Fedora), you can install (or upgrade to) the latest released
version, which will very likely be more recent than the version that comes
with your distribution::

    sudo easy_install -U kaa-imlib2

The most recent in-development version can be obtained via subversion::

    svn co svn://svn.freevo.org/kaa/trunk/imlib2 kaa-imlib2


API Documentation
=================

.. toctree::
   :maxdepth: 2

   image
   font

How do I use kaa.imlib2?
------------------------

Here are some examples to give you a feeling for basic usage.

First, import the module:

>>> from kaa import imlib2

Imlib2 supports most common image formats (jpeg, png, gif, tiff, bmp, etc.),
and can be loaded with :func:`imlib2.open`, which returns an
:class:`~imlib2.Image` object:

>>> img = imlib2.open('file.png')
>>> img
<kaa.imlib2.Image object size=1920x1080 at 0xb74c470c>

By default, decoded images are cached internally so that subsequent loads
pull from the cache.  If for some reason you want to bypass the cache, you
can use :func:`imlib2.open_without_cache`:

>>> img = imlib2.open_without_cache('file.png')

Or, you can disable caching altogether:

>>> imlib2.set_cache_size(0)
>>> imlib2.get_cache_size()
0L

There are a number of useful properties:

>>> img.filename, img.format, img.width, img.height
('file.png', 'png', 1920, 1080)

Rasterizing SVG into :class:`~imlib2.Image` objects is supported (provided
libsvg support is compiled into kaa.imlib2).  You can render the SVG at the
native resolution (if one is stored in the SVG) or at a custom resolution:

>>> img = imlib2.open('file.svg', (1920, 1080))

If you have an image file in memory, you can decode directly from the buffer
using :func:`imlib2.open_from_memory`.

Lastly, you can create a :func:`~imlib2.new` image, optionally with a pixel
buffer (in some RGB colorspace, e.g. ``BGRA``, ``RGB``, ``ARGB``, etc.):

>>> img = imlib2.new((1920, 1080))

Many manipulations to :class:`~imlib2.Image` objects are possible.  Some
return new objects, while others return self (to allow for convenient chaining
of manipulations); you'll need to consult the method documentation to see
what the return value is.

>>> img.draw_rectangle((10, 10), (-10, -10), '#ff0000aa')
<kaa.imlib2.Image object size=1920x1080 at 0x8571c0c>

Notice that sizes can be negative (and zero), in which case they produce a
width or height relative to the far edge of the image.  Negative positions are
also relative to the edge.  Also notice that colors can be specified as the
familiar hex color code used in HTML.  3- or 4-tuples of RGB[A] values are also
supported.

You can overlay other images using the flexible :meth:`~imlib2.Image.blend`
method, which lets you scale, crop, and composite simultaneously:

>>> watermark = imlib2.open('watermark.png')
>>> img.blend(watermark, dst_pos=(-watermark.width, -watermark.height), alpha=180)

Imlib2 can render text from TrueType fonts.  You first need to tell Imlib2
where to find fonts, but kaa.imlib2 offers a convenience function to initialize
the font path from what Fontconfig knows:

>>> imlib2.auto_set_font_path()

Then you reference the font names based on the (case-sensitive) filename of
the ``.ttf`` file.  Assuming you had ``VeraBd`` in your font path:

>>> img.draw_text((50, 50), 'Hello world!', '#ffffff', 'VeraBd/60')
(546, 92, 546, 93)

The return value shows the metrics of the rendered text.
:meth:`imlib2.Image.draw_text` has many options to render text.  It also supports
text styles such as drop shadows and outlines.  Rather than specifying the font
name, size, style, color, etc. each time, you can instead create a :class:`~imlib2.Font`
object and assign it to the image's :attr:`~imlib2.Image.font` property:

>>> img.font = imlib2.Font('VeraBd/60', '#ffffff')
>>> img.font.set_style(imlib2.TEXT_STYLE_SOFT_SHADOW, shadow='#558855')
>>> img.draw_text((50, 200), 'Uses the default style')
(989, 92, 989, 93)
>>> img.draw_text((50, 400), 'But you can still override', color='#ff000055',
...               shadow='#00ff00aa')
(1134, 92, 1134, 93)

One benefit of using Font objects is access to the method
:func:`~imlib2.Font.get_text_size`, to precompute the metrics of the text
as it would be rendered.  This is useful if, for example, you want to center
text, or otherwise position it where you'd need to know the rendered size
beforehand.

>>> img.font.size = 90
>>> w, h = img.font.get_text_size('Centered')[:2]
>>> img.draw_text(((img.width - w) / 2, (img.height - h) / 2), 'Centered')
(618, 139, 618, 139)

The above is just a small sample of what can be done with kaa.imlib2.  Refer
to the library documentation for full details and more examples.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
