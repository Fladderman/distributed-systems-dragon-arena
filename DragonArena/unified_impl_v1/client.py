import threading, time, json, socket, sys, os, logging
import messaging, das_game_settings, client_player, protected
from random import shuffle
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
from DragonArenaNew import DragonArena

class Client:
    def __init__(self, player):
        #TODO player reconnect after crash
        #TODO handle S2C_REFUSE

        assert isinstance(player, client_player.Player)
        self._player = player
        self.sorted_server_ids = self._ordered_server_list() #in order of descending 'quality
        print('self.sorted_server_ids', self.sorted_server_ids)
        self._server_socket = self._connect_to_a_server()
        print('self._server_socket', self._server_socket)
        m = messaging.M_C2S_HELLO()
        print('about to send msg', str(m))
        messaging.write_msg_to(self._server_socket, m)
        reply_msg = messaging.read_msg_from(self._server_socket, timeout=None)
        print('client got', str(reply_msg), ':)')
        assert reply_msg.header_matches_string('S2C_WELCOME')
        self._my_id = reply_msg.args[0]
        print('so far so good')
        first_update = messaging.read_msg_from(self._server_socket, timeout=None)
        print('client got', str(first_update), ':)')
        assert first_update.header_matches_string('UPDATE')
        # todo get state from server
        print('OK will try deserialize')
        self._protected_game_state = protected.ProtectedDragonArena(
            DragonArena.deserialize(first_update.args[1])
        )
        #TODO it seems like
        print('OK deserialized correctly')

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
    def sock_client(ip, port, timeout=1.0):
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
        print('main loop!')
        incoming_thread = threading.Thread(
            target=self.main_incoming_loop,
            args=(),
        )
        incoming_thread.daemon = True
        incoming_thread.start()
        self.main_outgoing_loop()

    def main_incoming_loop(self):
        print('main incoming')
        for msg in messaging.generate_messages_from(self._server_socket, timeout=None):
            print(str(msg))
            if msg != None:
                if msg.header_matches_string('UPDATE'):
                    new_state = DragonArena.deserialize(msg.args[1])
                    self._protected_game_state.replace_arena(new_state)
                    print('replaced arena! :D')
            else:
                print('AAAAAAAAAAAAAAAAAAAAAAAAAAAAHHHHHHHHHHHHHHHHH')


    def main_outgoing_loop(self):
        req_generator = self._player.main_loop(self._protected_game_state, self._my_id)
        for request in req_generator:
            print('player yielded request', request)
            assert isinstance(request, messaging.Message)
            print('forwarding', request)
            try:
                messaging.write_msg_to(self._server_socket, request)
            except:
                print('failed to write outbound requests!')
