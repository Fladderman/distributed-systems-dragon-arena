'''
This class is used by servers
it is meant for servers to keep track of other servers
'''

class ServerModel:
    def __init__(self, num_servers, my_id):
        self._server_id = my_id
        self.sockets = [None for _ in range(num_servers)]
        self.loads = [None for _ in range(num_servers)]
        self.loads[self._server_id] = 0

    def update_load(self, server_id, load):
        self.loads[server_id] = load

    def update_socket(self, server_id, maybe_sock):
        self.sockets[server_id] = maybe_sock

    def get_load_of(self, server_id):
        if self.sockets[server_id] is None:
            return None
        else:
            return self.loads[server_id]

    def tot_peer_load(self):
        tot = 0.0
        count = 0
        for i, load in enumerate(self.loads):
            if i != self._server_id and load is not None:
                count += 1
                tot += load
        return tot

    def count_peers(self):
        return len(filter x: x is not None, self.sockets)

    def avg_peer_load(self):
        n = self.count_peers()
        if n == 0: return None
        else:      return self.tot_peer_load() / n
