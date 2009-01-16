kaa.candy documentation
========================

**Third generation Canvas System using Clutter as backend**

kaa.candy is a module using clutter as canvas backend for the drawing operations.
It provides a higher level API for the basic clutter objects like Actor,
Timeline and Behaviour. The four main features are:

1. More complex widgets. Clutter only supports basic actors Text, Texture,
   Rectangle and Group. kaa.canvas uses these primitives to create more
   powerful widgets.

2. More powerful scripting language. The clutter scripting language is very
   primitive. With candyxml you can define higher level widgets and they can
   react on context changes with automatic redraws.

3. Better thread support. In kaa.candy two mainloops are running. The first one is
   the generic kaa mainloop and the second one is the clutter mainloop based on the
   glib mainloop. kaa.candy defines secure communication between these two mainloops.

4. Template engine. Instead of creating a widget it is possible to create a
   template how to create a widget. The candyxml module uses templates for faster
   object instantiation.

Contents:

.. toctree::
   :maxdepth: 2

   architecture
   widgets/index
   stage
   modifier
   animation
   candyxml



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
