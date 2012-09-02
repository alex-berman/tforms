import time

class Smoother:
    DEFAULT_RESPONSE_FACTOR = 5

    def __init__(self, response_factor=None):
        if response_factor is None:
            response_factor = self.DEFAULT_RESPONSE_FACTOR
        self._response_factor = response_factor
        self._current_value = None

    def smooth(self, new_value):
        now = time.time()
        if self._current_value:
            time_increment = now - self._time_of_previous_update
            self._current_value += (new_value - self._current_value) * \
                self._response_factor * time_increment
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

class ActivityBasedScope:
    def __init__(self, padding=0.5):
        self._padding = padding
        self._smoothed_min_value = Smoother(0.5)
        self._smoothed_max_value = Smoother(0.5)

    def update(self, target_min, target_max):
        self._smoothed_min_value.smooth(target_min)
        self._smoothed_max_value.smooth(target_max)
        self._offset = self._smoothed_min_value.value()
        diff = (self._smoothed_max_value.value() - self._offset) * (1 + self._padding)
        if diff == 0:
            self._ratio = 1
        else:
            self._ratio = 1.0 / diff

    def map(self, value):
        return self._ratio * (value - self._offset)

    def ratio(self):
        return self._ratio
