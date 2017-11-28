import threading, time, json, socket
import messaging, das_game_settings, client_player, state_dummy, protected_queue, protected_game_state
from random import shuffle

class Client:
    def __init__(self, player):
        assert isinstance(player, client_player.Player)
        self._player = player
        self.sorted_server_ids = self._ordered_server_list() #in order of descending 'quality
        print('self.sorted_server_ids', self.sorted_server_ids)
        self._server_socket = self._connect_to_a_server()
        print('self._server_socket', self._server_socket)
        m = messaging.M_C2S_HELLO
        print('about to send msg', str(m))
        messaging.write_msg_to(self._server_socket, m)
        reply_msg = messaging.read_msg_from(self._server_socket, timeout=False)
        print('client got', str(reply_msg), ':)')

        self._protected_game_state = protected_game_state.PotectedGameState()


    def _ordered_server_list(self):
        # todo ping etc etc
        x = range(0, len(das_game_settings.server_addresses))
        shuffle(x)
        return x

    def _connect_to_a_server(self):
        for i in range(0,10):
            print('connect loop', i)
            for serv_id in self.sorted_server_ids:
                ip, port = das_game_settings.server_addresses[serv_id]
                maybe_sock = Client.sock_client(ip, port)
                if maybe_sock is not None:
                    return maybe_sock
                else:
                    print('connection to', serv_id, 'failed...')
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
        # split thread into outgoing and incoming
        incoming_thread = threading.Thread(
            target=self._player.main_outgoing_loop,
            args=(,),
        )
        incoming_thread.daemon = True
        incoming_thread.start()
        main_incoming_loop()

    def main_incoming_loop(socket):
        for msg in messaging.read_many_msgs_from(socket):
            if msg != None:
                self._updates.push(msg)

    def main_outgoing_loop(self):
        self._player_requests = protected_queue.ProtectedQueue()
        # start off the player objects
        self._player_thread = threading.Thread(
            target=self._player.main_loop,
            args=(self._player_requests,self._protected_game_state),
        )
        self._player_thread.daemon = True
        self._player_thread.start()

        while True:
            drained = self._player_requests.drain()
            try:
                messaging.write_many_msgs_to(self._server_socket, drained)
            except:
                print('failed to write outbound requests')
