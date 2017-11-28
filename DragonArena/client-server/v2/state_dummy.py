
# JUST FOR TESTING!
class StateDummy:
    def __init__(self):
        self.data = {0:3, 1:"foo", 4.9:333, 'baz':0}
        self.data2 = [11,2,3,4,"bar"]

    def serialize(self):
        return (self.data, self.data2)

    @staticmethod
    def deserialize(serialized_state):
        data = serialized_state[0]
        data2 = serialized_state[1]
        assert isinstance(data, dict)
        assert isinstance(data2, list)
        s = StateDummy.__new__(StateDummy)
        s.data = data
        s.data2 = data2
        return s
