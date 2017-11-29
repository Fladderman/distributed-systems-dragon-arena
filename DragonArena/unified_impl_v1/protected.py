import threading, sys, os
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
from DragonArenaNew import DragonArena

class ProtectedDragonArena:
    def __init__(self, dragon_arena, timeout=0.1):
        assert isinstance(dragon_arena, DragonArena)
        assert isinstance(timeout, int) or isinstance(timeout, float)
        self._dragon_arena = dragon_arena
        self.timeout = timeout
        self._lock = threading.Lock()

    def replace_arena(self, new_dragon_arena):
        assert isinstance(new_dragon_arena, DragonArena)
        with self._lock:
            self._dragon_arena = new_dragon_arena

    '''
    caller can use this object by way of `with` semantics
    eg:
        with protected_dragon_arena as n:   #`with` block begins. return value of __enter__ bound to `n`. acquired lock
            n.foo()
            n.bar()
            x = n.get(3)
        # with block ends. __exit__ called. released lock

    '''
    def __enter__(self):
        self._lock.acquire()
        return self._dragon_arena

    def __exit__(self, type, value, traceback):
        self._lock.release()


class ProtectedQueue:
    def __init__(self, timeout=2.0):
        assert isinstance(timeout, int) or isinstance(timeout, float)
        self._cv = threading.Condition()
        self._q = []

    def dequeue(self, timeout=1.0):
        with self._cv:
            self._cv.wait(timeout=self.timeout)
            try: x = self._q.pop()
            except: return None

    def enqueue(self, x):
        with self._cv:
            self._q.append(x)
            self._cv.notifyAll()

    def drain(self, timeout=0.1):
        with self._cv:
            self._cv.wait(timeout=timeout)
            drained = self._q
            self._q = []
        return drained

    def contains(self, x, timeout=0.1):
        with self._cv:
            self._cv.wait(timeout=timeout)
            return x in self._q

    def drain_if_probably_something(self, timeout=0.1):
        return self.drain(timeout=timeout) if len(self._q) > 0 else []

    def enqueue_all_in(self, iterable):
        with self._cv:
            self._q.extend(iterable)
            self._cv.notifyAll()
