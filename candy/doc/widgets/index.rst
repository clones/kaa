.. _widgets:

Widgets
=======

Each widget has a clutter actor and functions starting with `_candy_` to
create and modify the clutter actors. These functions will always be
executed in the clutter mainloop. Do not access the internal object from
any other function.

For basic functions read the Widget class documentation and the clutter
`Actor API <http://www.clutter-project.org/docs/clutter/0.8/ClutterActor.html>`_

TODO: Describe Font, Color, and Context somewhere

.. toctree::
   :maxdepth: 2

   base
   group
   text

TODO: Describe Grid, Image widgets, Progressbar, and Rectangle
