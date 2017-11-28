import threading

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
