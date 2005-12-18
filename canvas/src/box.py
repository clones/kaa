__all__ = [ 'VBox', 'HBox' ]

from container import *

class Box(Container):
    def __init__(self, dimension):
        super(Box, self).__init__()
        self._dimension = dimension
        self._child_offsets = []
        self._child_sizes = []


    def _request_reflow(self, what_changed = None, old = None, new = None, child_asking = None):
        self._force_sync_property("pos")#, exclude = child_asking)
        self._force_sync_property("size")#, exclude = child_asking)
        if what_changed == "size" and old and old[self._dimension] == new[self._dimension]:
            return

        if self.get_canvas():
            self._calculate_child_offsets()

    def _request_expand(self, child_asking):
        self._request_reflow()

    #def _sync_property_size(self):
    #    self._calculate_child_offsets()
    #    return super(Box, self)._sync_property_size()


    def _calculate_child_offsets(self):
        self._child_sizes = []
        self._child_offsets = []
        allocated_size = n_expanded = expand_size = 0

        size = self._get_computed_size()[self._dimension]
        for child in self._children:
            if child["expand"] == True:
                self._child_sizes.append(None)
                n_expanded += 1
            else:
                child_size = child.get_computed_size()[self._dimension]
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
        if child_asking:
            min_dim = 0
            n_expanded = n_not_expanded = 0
            for child in self._children:
                if child["expand"] == True:
                    n_expanded += 1
                    continue
                    
                if child == child_asking:
                    continue
                child_size = child._get_minimum_size()
                min_dim += child_size[self._dimension]

            available = size[self._dimension] - min_dim
            if n_expanded > 0:
                if not child_asking["expand"]:
                    size[self._dimension] = child_asking._get_minimum_size()[self._dimension]
                else:
                    # FIXME: could end up offering an extent less than min
                    # size; should borrow space from another child if possible.
                    size[self._dimension] = available / n_expanded
            else:
                size[self._dimension] = available

        return size
        

    def _get_actual_size(self, child_asking = None):
        size = [0, 0]
        for child in self._children:
            child_size = child._get_computed_size()
            size[self._dimension] += child_size[self._dimension]
            size[1 - self._dimension] = max(size[1 - self._dimension], child_size[1 - self._dimension])
        return size

    def _get_minimum_size(self):
        size = [0, 0]
        for child in self._children:
            child_size = child._get_minimum_size()
            size[self._dimension] += child_size[self._dimension]
            size[1 - self._dimension] = max(size[1 - self._dimension], child_size[1 - self._dimension])
        return size



class HBox(Box):
    def __init__(self):
        super(HBox, self).__init__(dimension = 0)



class VBox(Box):
    def __init__(self):
        super(VBox, self).__init__(dimension = 1)


