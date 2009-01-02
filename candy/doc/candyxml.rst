CandyXML
========

**XML based scripting language for kaa.candy**

CandyXML is an XML based way to define widgets dependencies not using
Python code. It may be used to define themes for applications. It is
more powerful than clutter script and can be extended with application
specific widgets.

Widget Definition
-----------------

The basic idea is that every widget has a name to be used in an XML
file. This is done by the class variable `candyxml_name` of each
widget class. This name may be unique. If it is not, `candyxml_style`
must also be defined so the parser knows which class to use on object
creation. Each widget must provide a `candyxml_parse` function how to
parse the XML attributes and subnodes to arguments that can be used to
create an object of that class.

Example::

  class Foo(kaa.candy.Widget):
      candyxml_name = 'foo'
      @classmethod
      def candyxml_parse(cls, element):
          ...

  class SimpleBar(kaa.candy.Widget):
      candyxml_name = 'bar'
      candyxml_style = 'simple'
      @classmethod
      def candyxml_parse(cls, element):
          ...

  class ComplexBar(kaa.candy.Widget):
      candyxml_name = 'bar'
      candyxml_style = 'complex'
      @classmethod
      def candyxml_parse(cls, element):
          ...

XML example::

  <foo .../>                   --> Foo()
  <bar style='simple' .../>    --> SimpleBar()
  <bar style='complex' .../>   --> ComplexBar()

See :ref:`widgets` about additional details how to write the Python
part and see the `candyxml_parse` documentation of each widget about
how to use that widget in an XML file.

XML File Parsing
----------------

The root element of the XML file can be chosen by the application. It
must have width and height attributes and you must also provide width
and height for the parsing function. If they do not match, some values
like position and size of the widgets are changed on parsing. This
makes it possible to define a theme in 800x600 and use it at a window
with 1024x768.

The subnodes of the root element can be created using the template
system. Each of these subnodes must have a unique name attribute. The
`parse` function will return a dict with these names and the template
objects to create the widgets.  The XML parser will not create
widgets, it only creates templates.  Note: if the name contains a
minus it is converted into an underscore.

XML Example::

  <xandyxml width='800' height='600'>
      <container name='many-bars'>
          <bar x='10' y='0' style='simple' .../>
          <bar x='10' y='100' style='complex' .../>
      </container>
      <foo name='one-foo' .../>
      <foo name='something' .../>
  </candyxml>

Usage in Python::

  attr, elements = kaa.candy.candyxml.parse(filename, (1024, 768))
  stage.add(elements.container.many_bars)
  stage.add(elements.foo.one_foo)
  stage.add(elements.foo.something)

Context
-------

In some cases you do not know all attributes of the widget when
writing the XML file, e.g. an image should show the image defined by
the `filename` attribute of an object you create during
runtime. kaa.candy has support for creating widgets based on a
context. Changing the context may change the whole window with one
command. The concept is to split the logic into three parts: the
layout (candyxml), the content (context) and the application logic
(your code).  For images and text widgets the magic key is `$`. See
the documentation of the specific widgets if they are context
sensitive or not.

XML Example::

  <xandyxml width='800' height='600'>
      <container name='test'>
          <image filename='$background'/>
          <image filename='$item.filename'/>
      </container>
  </candyxml>

Python Code::

  # context to use, MyImage has a memeber variable filename
  context = dict(background='bg.jpg', item=MyImage())
  # create container widget based on the context.
  container = elements.container.test(context=context)
  ...
  # change item and this will change item.filename
  context['item'] = MyImage2()
  # change the container, this will replace the second image
  container = elements.container.test(context=context)

This makes creating application specific themes very easy. You can
define new widgets for your application. E.g. an audio player: define
where to draw the cover, title, etc and every time a new track starts
you can set a new context and the whole GUI will redraw on its own.
