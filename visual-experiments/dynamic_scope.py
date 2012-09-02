import time

class Smoother:
    RESPONSE_FACTOR = 5

    def __init__(self):
        self._current_value = None

    def smooth(self, new_value):
        now = time.time()
        if self._current_value:
            time_increment = now - self._time_of_previous_update
            self._current_value += (new_value - self._current_value) * \
                self.RESPONSE_FACTOR * time_increment
        else:
            self._current_value = new_value
        self._time_of_previous_update = now

    def value(self):
        return self._current_value


class DynamicScope:
    def __init__(self, padding=0):
        self._padding = padding
        self._smoothed_min_value = Smoother()
        self._smoothed_max_value = Smoother()
        self._min_value = None
        self._max_value = None

    def put(self, value):
        self._min_value = min(filter(lambda x: x is not None, [self._min_value, value]))
        self._max_value = max(filter(lambda x: x is not None, [self._max_value, value]))
        self.update()

    def update(self):
        if self._min_value is not None:
            self._smoothed_min_value.smooth(self._min_value)
            self._smoothed_max_value.smooth(self._max_value)
            self._offset = self._smoothed_min_value.value()
            diff = self._smoothed_max_value.value() - self._smoothed_min_value.value() + \
                self._padding * 2
            if diff == 0:
                self._ratio = 1
            else:
                self._ratio = 1.0 / diff

    def map(self, value):
        return self._ratio * (value - self._offset + self._padding)


class DensityDrivenScope:
    BLUR_RADIUS = 0.5

    def __init__(self, max_value, num_partitions=10, blur_radius=None):
        self._max_value = max_value
        self._num_partitions = num_partitions
        if blur_radius is None:
            blur_radius = self.BLUR_RADIUS
        self._absolute_blur_radius = int(num_partitions * blur_radius)
        self._create_partitions()
        self.update([])

    def _create_partitions(self):
        self._partitions = []
        for i in range(self._num_partitions):
            partition = {"input_offset": float(i) * self._max_value / self._num_partitions,
                         "density": 0}
            self._partitions.append(partition)

    def update(self, values):
        if len(values) > 0:
            for partition in self._partitions:
                partition["density"] = 0.0001

            for value in values:
                partition = self._partition_for_value(value)
                partition["density"] += 1

            if self._absolute_blur_radius > 0:
                for i in range(self._num_partitions):
                    self._blur_density(i)
                for partition in self._partitions:
                    partition["density"] = partition["blurred_density"]

            total_density = sum([partition["density"] for partition in self._partitions])
            for partition in self._partitions:
                partition["share"] = partition["density"] / total_density
        else:
            for partition in self._partitions:
                partition["share"] = 1.0 / self._num_partitions

        output_offset = 0
        for partition in self._partitions:
            partition["output_range"] = self._max_value * partition["share"]
            partition["output_offset"] = output_offset
            output_offset += partition["output_range"]

        #print values; for i in range(self._num_partitions): print i, self._partitions[i]

    def _blur_density(self, n):
        n1 = max(n - self._absolute_blur_radius, 0)
        n2 = min(n + self._absolute_blur_radius, self._num_partitions)
        self._partitions[n]["blurred_density"] = sum(
            [self._partitions[i]["density"] for i in range(n1, n2)]) / (n2 - n1)

    def map(self, input_value):
        partition = self._partition_for_value(input_value)
        output_value = (partition["output_offset"] + \
            (input_value - partition["input_offset"]) * \
                            partition["share"] * self._num_partitions) / \
            self._max_value
        #print "map(%s)=%s" % (input_value, output_value)
        return output_value

    def _partition_for_value(self, input_value):
        for partition in reversed(self._partitions):
            if partition["input_offset"] <= input_value:
                return partition
