__all__ = [ 'VBox', 'HBox' ]

from container import *

class Box(Container):
    def __init__(self, dimension):
        super(Box, self).__init__()
        self._dimension = dimension
        self._child_offsets = []
        self._child_sizes = []


    def _request_reflow(self, what_changed = None, old = None, new = None, child_asking = None):
        #print "[BOX REFLOW]", self, child_asking, what_changed, old, new
        if not super(Box, self)._request_reflow(what_changed, old, new, child_asking):
            # Box._request_reflow will return False if our size hasn't 
            # changed, in which case we don't need to respond to this reflow
            # request.
            return False

        if what_changed == "size" and child_asking and old and old[self._dimension] == new[self._dimension]:
            return True

        if self.get_canvas():
            self._force_sync_property("pos")
            self._calculate_child_offsets()

        return True

    def _request_expand(self, child_asking):
        self._request_reflow()


    def _calculate_child_offsets(self):
        self._child_sizes = []
        self._child_offsets = []
        allocated_size = n_expanded = expand_size = 0

        #print "[OFFSETS]:", self
        size = self._get_computed_size()[self._dimension]
        for child in self._children:
            if child["expand"] == True:
                self._child_sizes.append(None)
                n_expanded += 1
            else:
                child_size = child.get_computed_size()[self._dimension]
                # Children with fixed coordinates adjust the size they occupy
                # in the box.
                if type(child["pos"][self._dimension]) == int:
                    child_size += child["pos"][self._dimension]
                allocated_size += child_size
                self._child_sizes.append(child_size)

        if n_expanded > 0:
            expand_size = (size - allocated_size) / n_expanded

        for i in range(len(self._children)):
            if self._child_sizes[i] == None:
                self._child_sizes[i] = expand_size
            if i == 0:
                self._child_offsets.append(0)
            else:
                self._child_offsets.append(self._child_offsets[i-1] + self._child_sizes[i-1])

        #print " < ", self, self._child_sizes, " - offsets", self._child_offsets
        

    def _get_computed_pos(self, child_asking = None):
        pos = list(super(Box, self)._get_computed_pos(child_asking))
        #self._calculate_child_offsets()
        if child_asking:
            index = self._children.index(child_asking)
            if index < len(self._child_offsets):
                pos[self._dimension] = pos[self._dimension] + self._child_offsets[index]
        return pos

    def _get_computed_size(self, child_asking = None):
        size = list(super(Box, self)._get_computed_size(child_asking))
        if child_asking:
            index = self._children.index(child_asking)
            if index < len(self._child_sizes):
                size[self._dimension] = self._child_sizes[index]
        return size


    def _get_extents(self, child_asking = None):
        size = list(super(Box, self)._get_extents(child_asking))
        if not child_asking:
            return size

        #print "[EXTENTS]: ", self, child_asking, size
        minimal_size = 0
        size_requested = 0
        n_expanded = 0
        sizes = {}
        for child in self._children:
            min_child_size = list(child._get_minimum_size())
            req_child_size = list(child._compute_size(child["size"], None, size))
            if type(child["pos"][self._dimension]) == int:
                min_child_size[self._dimension] += child["pos"][self._dimension]
                req_child_size[self._dimension] += child["pos"][self._dimension]

            sizes[child] = (min_child_size, req_child_size)

            if child["expand"] == True:
                n_expanded += 1
                continue

            if child == child_asking:
                continue

            minimal_size += min(min_child_size[self._dimension], req_child_size[self._dimension])
            size_requested += req_child_size[self._dimension]


        if n_expanded == 0:
            # No children are expanded.
            if size_requested <= size[self._dimension]:
                # We have enough size to accommodate them.
                return size
            # FIXME: children asking for more size than is available, need to
            # handle this.  For now, just let them use what they want.
            return size

        if not child_asking["expand"]:
            # FIXME: child could be asking for too much size here as well.
            return size
        else:
            available = size[self._dimension] - size_requested
            # Split available size among number of expanded children.
            size[self._dimension] = available / n_expanded

        #print "< extents", self, child_asking, size
        return size
        

    def _get_size_common(self, sizefunc):
        size = [0, 0]
        for child in self._children:
            child_size = list(getattr(child, sizefunc)())
            # Children with fixed coordinates adjust the size they occupy
            # in the box.
            if type(child["pos"][0]) == int:
                child_size[0] += child["pos"][0]
            if type(child["pos"][1]) == int:
                child_size[1] += child["pos"][1]

            size[self._dimension] += child_size[self._dimension]
            size[1 - self._dimension] = max(size[1 - self._dimension], child_size[1 - self._dimension])
        return size


    def _get_actual_size(self, child_asking = None):
        return self._get_size_common("_get_computed_size")


    def _get_minimum_size(self):
        return self._get_size_common("_get_minimum_size")


class HBox(Box):
    def __init__(self):
        super(HBox, self).__init__(dimension = 0)



class VBox(Box):
    def __init__(self):
        super(VBox, self).__init__(dimension = 1)


