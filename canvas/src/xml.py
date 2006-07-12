__all__ = ["create_canvas_tree", "get_object_from_xml"]

try:
    import libxml2
except ImportError:
    libxml2 = None

import kaa.canvas
import os
import re

def _get_full_path(filename, path):
    if filename[0] == "/":
        return filename

    for p in path:
        absfile = os.path.join(p, filename)
        if os.path.exists(absfile):
            return absfile

    raise ValueError, "Unable to locate file: %s" % filename


def _create_object_from_node(node, parent, path):
    o = None

    if node.name in ("canvas", "classes"):
        return parent

    elif node.name == "container":
        o = kaa.canvas.Container()

    elif node.name == "image":
        o = kaa.canvas.Image()
        if node.hasProp("file"):
            o.set_image(_get_full_path(node.prop("file"), path))
        if node.hasProp("border"):
            border = [ int(x) for x in node.prop("border").split() ]
            assert(len(border) == 4)
            o.set_border(*border)
        if node.hasProp("aspect"):
            o.set_aspect(node.prop("aspect"))

    elif node.name == "text" and not node.isText():
        o = kaa.canvas.Text()
        text = re.sub("\s+|\n", " ", node.content).strip()
        o.set_text(text)
        if node.hasProp("font"):
            o.set_font(font = node.prop("font"))
        if node.hasProp("size"):
            o.set_font(size = int(node.prop("size")))

    elif node.name == "rectangle":
        o = kaa.canvas.Rectangle()

    elif node.name == "vbox":
        o = kaa.canvas.VBox()
    elif node.name == "hbox":
        o = kaa.canvas.HBox()

    elif node.name == "movie":
        o = kaa.canvas.Movie()

    elif node.name == "textblock":
        lines = []
        child = node.children
        # There's probably a more elegant way to do this with libxml2,
        # but I'm far too lazy to actually RTFM.
        while child:
            lines.append(str(child))
            child = child.next
        o = kaa.canvas.TextBlock("".join(lines))

    else:
        raise ValueError, "Unknown canvas object '%s'" % node.name

    # Properties will be None if not specified, in which case they will be
    # ignored in resize()
    o.resize(width = node.prop("width"), height = node.prop("height"))
    o.move(left = node.prop("left"), top = node.prop("top"),
           right = node.prop("right"), bottom = node.prop("bottom"),
           hcenter = node.prop("hcenter"), vcenter = node.prop("vcenter"))

    if node.hasProp("visible"):
        if node.prop("visible").lower() in ("0", "no", "false"):
            o.set_visible(False)

    if node.hasProp("expand"):
        expand = node.prop("expand").lower()
        if expand in ("0", "no", "false"):
            o.set_expand(False)
        elif expand in ("1", "yes", "true"):
            o.set_expand(True)
        elif "%" in expand:
            o.set_expand(expand)

    if node.hasProp("color"):
        color = node.prop("color")
        if color[0] == "#":
            o.set_color(color)
        else:
            o.set_color(*tuple(color))
    if node.hasProp("alpha"):
        o.set_color(a = int(node.prop("alpha")))
    if node.hasProp("name"):
        name = node.prop("name")
        if name[0] == ".":
            name = name[1:]
            # Concatenate to parent
            if parent.get_name():
                name = "%s.%s" % (parent.get_name(), name)
        o.set_name(name)
         
    if node.hasProp("clip"):   
        clip = node.prop("clip")
        if clip == "auto":
            o.clip("auto")
        else:
            clip = clip.split()
            assert(len(clip) == 4)
            o.clip(clip[:2], clip[2:])

    if node.hasProp("layer"):
        o.set_layer(int(node.prop("layer")))

    if parent:
        parent.add_child(o)
    return o


def _process_node(node, parent, path, clsname):
    child = node.children
    while child:
        if child.name == "comment":
            child = child.next
            continue

        obj = None
        if not child.isText() and (not clsname or clsname == child.prop("class")):
            if child.name == "canvas" and clsname and not parent:
                raise Exception, "Use Canvas.from_xml to get canvas objects."

            obj = _create_object_from_node(child, parent, path)
            assert(obj)

        if child.children and not isinstance(obj, (kaa.canvas.Text, kaa.canvas.TextBlock)):
            c = clsname
            if obj:
                c = None
            else:
                obj = parent
            obj = _process_node(child, obj, path, c)

        if obj and clsname:
            return obj

        child = child.next

    return parent


def _get_doc(filename_or_string):
    if "<" in filename_or_string:
        return libxml2.parseMemory(filename_or_string, len(filename_or_string))
    else:
        return libxml2.parseFile(filename_or_string)


def create_canvas_tree(filename_or_string, canvas_object, classname = None, path = []):
    if not libxml2:
        raise SystemError, "libxml2 not present on this system; XML support not available."
    doc = _get_doc(filename_or_string)
    _process_node(doc, canvas_object, ["."] + path, classname)


def get_object_from_xml(filename_or_string, classname, path = []):
    if not libxml2:
        raise SystemError, "libxml2 not present on this system; XML support not available."
    doc = _get_doc(filename_or_string)
    return _process_node(doc, None, ["."] + path, classname)
