import threading
import time
import socket
import messaging
import das_game_settings
import client_player
import protected
from random import shuffle
from DragonArenaNew import DragonArena
from messaging import Message, MessageError
from das_game_settings import debug_print
from math import sqrt
import random
import os


class Client:
    def __init__(self, player):
        # TODO player reconnect after crash
        # TODO handle S2C_REFUSE

        assert isinstance(player, client_player.Player)
        self._player = player
        # in order of descending 'quality
        self.sorted_server_ids = Client._ordered_server_list()
        debug_print('self.sorted_server_ids', self.sorted_server_ids)
        self._connect_to_a_server()

    def _connect_to_a_server(self, reconnect=False):
        backoff = 0.05
        while True:
            for serv_id in self.sorted_server_ids:
                try:
                    ip, port = das_game_settings.server_addresses[serv_id]
                    debug_print('Trying server at', ip, port)
                    '''1. get socket'''
                    self._server_socket = Client.sock_client(ip, port)
                    if self._server_socket is None:
                        continue
                    debug_print('self._server_socket', self._server_socket)
                    '''2. send hello'''
                    if not reconnect:
                        self._random_salt = random.randint(0, 999999)
                        hello_msg = messaging.M_C2S_HELLO(self._random_salt)
                    else:
                        hello_msg = messaging.M_C2S_HELLO_AGAIN(
                            self._random_salt, self._my_id, self._secret)

                    debug_print('about to send msg', str(hello_msg))
                    messaging.write_msg_to(self._server_socket, hello_msg)
                    '''2. get reply (expect welcome)'''
                    reply_msg = messaging.read_msg_from(
                        self._server_socket,
                        timeout=das_game_settings.client_handshake_timeout)
                    debug_print('expecting welcome. client got',
                                str(reply_msg), ':)')
                    if messaging.is_message_with_header_string(reply_msg,
                                                               'S2C_REFUSE'):
                        debug_print('got refused!')
                        continue
                    if not messaging.is_message_with_header_string(reply_msg,
                                                                   'S2C_WELCOME'):
                        raise RuntimeError('crash or timeout')
                    '''3. get my knight's ID'''
                    self._my_id = tuple(reply_msg.args[0])
                    self._secret = reply_msg.args[1]
                    debug_print('so far so good')
                    '''4. wait for 1st game update'''
                    first_update =\
                        messaging.read_msg_from(
                            self._server_socket,
                            timeout=max(das_game_settings.max_done_wait,
                                        das_game_settings.client_handshake_timeout))
                    debug_print('expecting update. client got',
                                str(first_update))
                    if not messaging.is_message_with_header_string(
                            first_update, 'UPDATE'):
                        raise RuntimeError('got' + str(first_update) +
                                           'instead of first update')

                    '''5. try deserialize and extract game state'''
                    self._protected_game_state = protected.ProtectedDragonArena(
                        DragonArena.deserialize(first_update.args[1])
                    )
                    debug_print('OK deserialized correctly')
                    return # exit the loop
                except Exception as e:
                    debug_print('CONNECTION WENT AWRY :(', e)
            debug_print('failed to connect to everyone! D:')
            time.sleep(backoff)
            debug_print('backing off...', backoff)
            backoff = sqrt(backoff * 2)

    @staticmethod
    def _ordered_server_list():
        server_addresses = das_game_settings.server_addresses  # long name
        rtts = [
            Client.measure_rtt_to(*addr)
            for addr in server_addresses
        ]
        # sort server addresses according to rtts
        ordered = [i for _, i in sorted(zip(rtts,
                                            range(len(server_addresses))))]
        debug_print('rtts', rtts)
        debug_print('ordered', ordered)

        # todo ping etc etc
        x = range(0, len(das_game_settings.server_addresses))
        shuffle(x)
        return x

    @staticmethod
    def measure_rtt_to(ip, port):
        debug_print('rtt to...', ip, port, 'is...')
        start_time = time.time()
        result = Client.sock_client(
            ip, port, timeout=das_game_settings.client_ping_max_time)
        rtt = (time.time() - start_time
               if result is not None
               else das_game_settings.client_ping_max_time)
        if result is not None:
            result.close()
        debug_print('rtt', rtt)
        time.sleep(0.7)
        return rtt


    '''
    attempts to connect
    '''
    @staticmethod
    def sock_client(ip, port, timeout=1.0):
        assert isinstance(ip, str)
        assert isinstance(port, int)
        assert isinstance(timeout, int) or isinstance(timeout, float)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.4)
            s.connect((ip, port))
            return s
        except:
            return None

    def main_loop(self):
        # split thread into outgoing and incoming
        debug_print('main loop!')
        incoming_thread = threading.Thread(
            target=self.main_incoming_loop,
            args=(),
        )
        incoming_thread.daemon = True
        incoming_thread.start()
        self.main_outgoing_loop()

    def main_incoming_loop(self):
        debug_print('main incoming')
        # while True:
        #     msg = messaging.read_msg_from(self._server_socket, timeout=None)
        for msg in messaging.generate_messages_from(self._server_socket,
                                                    timeout=None):
            debug_print(str(msg))
            if msg != MessageError.CRASH:
                if msg.header_matches_string('UPDATE'):
                    new_state = DragonArena.deserialize(msg.args[1])
                    self._protected_game_state.replace_arena(new_state)
                    debug_print('replaced arena! :D')
                    if new_state.game_over:
                        time.sleep(2.0)
                        print(('GAME OVER! {winners} win!'
                              ).format(winners=new_state.get_winner()))
                        os._exit(0)
            else:
                debug_print('Socket dead! incoming handler dying!')
                # return


    def main_outgoing_loop(self):
        req_generator = self._player.main_loop(self._protected_game_state,
                                               self._my_id)
        debug_print('ready?')
        for request in req_generator:
            debug_print('player yielded request', request)
            assert isinstance(request, Message)
            debug_print('forwarding', request)
            if not messaging.write_msg_to(self._server_socket, request):
                debug_print('failed to write outbound requests!')
                self._connect_to_a_server(reconnect=True)
                incoming_thread = threading.Thread(
                    target=self.main_incoming_loop,
                    args=(),
                )
                incoming_thread.daemon = True
                incoming_thread.start()
                print('Recovered :D')

        debug_print('no more requests')
