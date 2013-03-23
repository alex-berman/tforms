class Smoother:
    RESPONSE_FACTOR = 5

    def __init__(self, response_factor=None):
        if response_factor is None:
            response_factor = self.RESPONSE_FACTOR
        self._current_value = None
        self._response_factor = response_factor

    def smooth(self, new_value, time_increment):
        if self._current_value:
            self._current_value += (new_value - self._current_value) * \
                self._response_factor * min(time_increment, 1.0)
        else:
            self._current_value = new_value

    def value(self):
        return self._current_value

    def reset(self):
        self._current_value = None
