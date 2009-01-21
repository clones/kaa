Widget Base Class
=================

TODO: Add introduction

.. kaaclass:: candy.Widget

   .. classattrs::

        .. attribute:: ALIGN_LEFT
        .. attribute:: ALIGN_RIGHT
        .. attribute:: ALIGN_TOP
        .. attribute:: ALIGN_BOTTOM
        .. attribute:: ALIGN_CENTER
        .. attribute:: ALIGN_SHRINK

           Used by xalign and yalign to shrink the width or height to
           match the actual content of the underlying Clutter actor.

        .. attribute:: context_sensitive

	   Inherting class can on a context.

        .. attribute:: candyxml_name

        .. attribute:: candyxml_style

   .. automethods::
   .. autoproperties::

        .. attribute:: passive

	True if the widget should adjust its size based on the parent

        .. attribute:: subpixel_precision

        .. attribute:: name

	name of the widget to locate it again later in a group

