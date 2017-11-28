import threading
import state_dummy

class ProtectedGameState:
    def __init__(self, state, timeout=0.1):
        self._state = state
        self.timeout = timeout
        self._lock = threading.Lock()

    def apply_func(self, func): #VERY generic. supply a function to be applied
        assert callable(func)
        with self._lock:
            return func(state)

    def replace_state(self, new_state):
        assert isinstance(new_state, state_dummy.StateDummy)
        with self._lock:
            self._state = new_state


class ProtectedQueue:
    def __init__(self, timeout=2.0):
        assert isinstance(timeout, int) or isinstance(timeout, float)
        # self._lock = threading.Lock()
        self._cv = threading.Condition()
        self.timeout = timeout
        self._q = []

    def pop(self):
        x = None
        with self._cv:
            self._cv.wait(timeout=self.timeout)
            try: x = self._q.pop()
            except: pass
        return x

    def push(self, x):
        with self._cv:
            self._cv.notifyAll()
            self._q.append(x)

    def drain(self):
        with self._cv:
            self._cv.wait(timeout=self.timeout)
            drained = self._q
            self._q = []
        return drained

    def push_all(self, iterable):
        with self._cv:
            self._q.extend(iterable)
            self._cv.notifyAll()
