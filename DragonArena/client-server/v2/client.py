import threading, time, json, socket
import messaging, das_game_settings, client_player
from random import shuffle

class Client:
    def __init__(self, player):
        assert isinstance(player, client_player.Player)
        self._player = player;
        self.sorted_server_ids = self._ordered_server_list() #in order of descending 'quality
        self._server_socket = self._connect_to_a_server()
        messaging.write_msg_to(self._server_socket, messaging.CLIENT_HELLO)
        reply_msg = messaging.read_msg_from(serv_socket, timeout=False)
        print('client got', str(msg), ':)')
        self._player_requests = []


    def _ordered_server_list(self):
        # todo ping etc etc
        return shuffle(
            range(
                0,
                len(das_game_settings.server_addresses),
            )
        )

    self._connect_to_a_server(self):
        for _ in range(0,10):
            for serv_id in self.sorted_server_ids:
                ip, port = das_game_settings.server_addresses[serv_id]
                maybe_sock = Client.sock_client(ip, port)
                if maybe_sock is not None:
                    return maybe_sock
        raise "Couldn't connect to anybody :("


    '''
    attempts to connect
    '''
    @staticmethod
    def sock_client(ip, port, timeout=2.0):
        assert isinstance(ip, str)
        assert isinstance(port, int)
        assert isinstance(timeout, int) or isinstance(timeout, float)
        try:
            socket.setdefaulttimeout(timeout)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            return s
        except:
            return None

    def main_loop(self):
        # start off the player objects
        self._player_thread = threading.Thread(
            target=client_player.Player.main_loop
            args=(self._player, self._player_requests),
        )
        self._player_thread.daemon = True
        self._player_thread.start()

        while True:
            pass
