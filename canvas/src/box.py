__all__ = [ 'VBox', 'HBox' ]

from container import *

class Box(Container):
    def __init__(self, dimension):
        super(Box, self).__init__()
        self._dimension = dimension
        self._child_offsets = []
        self._child_sizes = []


    def _request_reflow(self, what_changed = None, old = None, new = None, child_asking = None, signal = True):
        #print "[BOX REFLOW]", self, child_asking, what_changed, old, new
        if not super(Box, self)._request_reflow(what_changed, old, new, child_asking, False):
            # Box._request_reflow will return False if our size hasn't 
            # changed, in which case we don't need to respond to this reflow
            # request.

            # FIXME: technically not true: if child A grows by 5 and child B
            # shinks by 5, our size hasn't changed, but we do need to
            # recalculate offsets.
            return False

        if what_changed == "size" and child_asking and old and old[self._dimension] == new[self._dimension]:
            if signal:
                self.signals["reflowed"].emit()
            return True

        if self.get_canvas():
            self._force_sync_property("pos")
            self._calculate_child_offsets()

        if signal:
            self.signals["reflowed"].emit()
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
            if not child["display"]:
                self._child_sizes.append(0)
                self._child_offsets.append(0)
                continue

            if child["expand"] == True:
                self._child_sizes.append(None)
                n_expanded += 1
            else:
                child_size = child._get_computed_size()[self._dimension]
                # Children with fixed coordinates adjust the size they occupy
                # in the box.
                child_pos = child._get_fixed_pos()[self._dimension]
                child_margin = child._get_computed_margin()
                child_size += child_margin[1-self._dimension] + child_margin[1-self._dimension + 2]
                if child_pos != None:
                    child_size += child_pos
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
        

    def _get_computed_pos(self, child_asking = None, with_margin = True):
        pos = list(super(Box, self)._get_computed_pos(child_asking, with_margin))
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
            if not child["display"]:
                continue
            min_child_size = list(child._get_minimum_size())
            req_child_size = list(child._compute_size(child["size"], None, size))
            for i in range(2):
                child_margin = child._get_computed_margin()
                min_child_size[i] += child_margin[1-i] + child_margin[1-i+2]
                req_child_size[i] += child_margin[1-i] + child_margin[1-i+2]

            child_pos = child._get_fixed_pos()[self._dimension]
            if child_pos != None:
                min_child_size[self._dimension] += child_pos
                req_child_size[self._dimension] += child_pos

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
            if not child["display"]:
                continue
            child_size = list(getattr(child, sizefunc)())
            child_margin = child._get_computed_margin()
            child_size[0] += child_margin[1] + child_margin[3]
            child_size[1] += child_margin[0] + child_margin[2]

            # Children with fixed coordinates adjust the size they occupy
            # in the box.
            child_pos = child._get_fixed_pos()
            if child_pos[0] != None:
                child_size[0] += child_pos[0]
            if child_pos[1] != None:
                child_size[1] += child_pos[1]

            size[self._dimension] += child_size[self._dimension]
            size[1 - self._dimension] = max(size[1 - self._dimension], child_size[1 - self._dimension])

        # If container has a fixed dimension, override calculated dimension.
        padding = self._get_computed_padding()
        for i in range(2):
            if type(self["size"][i]) == int:
                size[i] = self["size"][i]
            else:
                size[i] += padding[1-i] + padding[1-i+2]


        return size


    def _get_intrinsic_size(self, child_asking = None):
        return self._get_size_common("_get_computed_size")


    def _get_minimum_size(self):
        return self._get_size_common("_get_minimum_size")


class HBox(Box):
    def __init__(self):
        super(HBox, self).__init__(dimension = 0)



class VBox(Box):
    def __init__(self):
        super(VBox, self).__init__(dimension = 1)


