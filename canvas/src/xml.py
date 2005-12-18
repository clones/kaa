__all__ = ["create_canvas_tree"]

import libxml2
import kaa.canvas
import os

# XXX !!! WARNING !!!  It is not safe to parse untrusted xml files with this
# code.  (Shameless use of eval())

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

    if node.name == "canvas":
        return parent

    elif node.name == "container":
        o = kaa.canvas.Container()

    elif node.name == "image":
        o = kaa.canvas.Image()
        if node.hasProp("file"):
            o.set_image(_get_full_path(node.prop("file"), path))
        if node.hasProp("border"):
            border = eval(node.prop("border"))
            o.set_border(*border)

    elif node.name == "text" and not node.isText():
        o = kaa.canvas.Text()
        o.set_text(node.content)
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

    else:
        raise ValueError, "Unknown canvas object '%s'" % node.name

    size = list(o.get_size())
    if node.hasProp("width"):
        size[0] = node.prop("width")
        if size[0].isdigit():
            size[0] = int(size[0])
    if node.hasProp("height"):
        size[1] = node.prop("height")
        if size[1].isdigit():
            size[1] = int(size[1])
    o.set_size(size)

    pos = list(o.get_pos())
    if node.hasProp("x"):
        pos[0] = node.prop("x")
        if pos[0].replace("-", "").isdigit():
            pos[0] = int(pos[0])
    if node.hasProp("y"):
        pos[1] = node.prop("y")
        if pos[1].replace("-", "").isdigit():
            pos[1] = int(pos[1])
    o.set_pos(pos)

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
        color = tuple(node["color"])
        o.set_color(*color)
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
            
    if node.hasProp("layer"):
        o.set_layer(int(node.prop("layer")))

    parent.add_child(o)
    return o


def _process_node(node, parent, path):
    child = node.children
    while child:
        if child.name == "comment":
            child = child.next
            continue

        obj = None
        if not child.isText():
            obj = _create_object_from_node(child, parent, path)
            assert(obj)

        if child.children:
            _process_node(child, obj, path)
        child = child.next
    

def create_canvas_tree(canvas_object, filename = None, string  = None, path = []):
    if filename:
        doc = libxml2.parseFile(filename)
    elif string:
        doc = libxml2.parseMemory(string, len(string))
    else:
        raise ValueError, "No xml source specified"

    _process_node(doc, canvas_object, path)


