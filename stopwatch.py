import time

class Stopwatch:
    def __init__(self):
        self._running = False

    def start(self):
        self._running = True
        self._real_time_started = time.time()

    def stop(self):
        self._running = False

    def restart(self):
        self.start()

    def running(self):
        return self._running

    def get_elapsed_time(self):
        if self.running():
            return time.time() - self._real_time_started
        else:
            return 0
