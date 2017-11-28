import threading

class PotectedGameState:
    def __init__(self, state, timeout=0.1):
        self._state = state
        self.timeout = timeout
        self._lock = threading.Lock()

    def apply_func(self, func):
        assert callable(func)
        with self._lock:
            return func(state)
