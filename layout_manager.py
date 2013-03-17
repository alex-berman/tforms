class LayoutManager1d:
    def __init__(self):
        self._components = {}
        self._id_count = 1

    def add(self, begin, end):
        for component in self._components.values():
            if self._overlap(component["begin"], component["end"], begin, end):
                return False
        layout_component = self._id_count
        self._components[layout_component] = {"begin": begin, "end": end}
        self._id_count += 1
        return layout_component

    def _overlap(self, begin1, end1, begin2, end2):
        return ((begin2 <= begin1 <= end2) or
                (begin2 <= end1 <= end2) or
                (begin1 <= begin2 <= end1) or
                (begin1 <= end2 <= end1))

    def remove(self, layout_component):
        del self._components[layout_component]
