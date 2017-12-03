import threading
import time
import socket
import logging
import messaging
import das_game_settings
import client_player
import protected
from DragonArenaNew import DragonArena
from messaging import Message, MessageError
from das_game_settings import debug_print
from math import sqrt
import random
from drawing import ascii_draw
import os
import string


def generate_name():
    return ''.join(random.choice(string.ascii_uppercase +
                                 string.ascii_lowercase +
                                 string.digits) for _ in range(6))


class Client:
    def __init__(self, player):
        # TODO player reconnect after crash
        # TODO handle S2C_REFUSE
        self._name = generate_name()
        log_filename = 'client_{name}.log'.format(name=self._name)
        logging.basicConfig(filename=log_filename,
                            filemode='a',
                            level=das_game_settings.logging_level,
                            format='%(asctime)s.%(msecs)03d <client:' +
                                   self._name + '> %(message)s',
                            datefmt='%a %H:%M:%S')
        logging.info("Client `{name}` started logging! :D".
                     format(name=self._name))

        assert isinstance(player, client_player.Player)
        self._player = player
        # in order of descending 'quality
        self.sorted_server_ids = Client._ordered_server_list()
        debug_print('self.sorted_server_ids', self.sorted_server_ids)
        self._connect_to_a_server()

    def _connect_to_a_server(self, reconnect=False):
        logging.info("Connecting to server...")
        backoff = 0.01
        while True:
            for serv_id in self.sorted_server_ids:
                try:
                    ip, port = das_game_settings.server_addresses[serv_id]
                    debug_print('Trying server at', ip, port)
                    logging.info("Trying server (id={serv_id}) at {ip} {port}".
                                 format(serv_id=serv_id,ip=ip,port=port))
                    '''1. get socket'''
                    self._server_socket = Client.sock_client(ip, port)
                    if self._server_socket is None:
                        logging.info("No dice.")
                        continue
                    logging.info("Got a socket! Sending HELLO")
                    debug_print('self._server_socket', self._server_socket)
                    '''2. send hello'''
                    if not reconnect:
                        self._random_salt = random.randint(0, 999999)
                        logging.info(("This is a fresh connection. "
                                      "my salt is {salt}").
                                     format(salt=self._random_salt))
                        hello_msg = messaging.M_C2S_HELLO(self._random_salt)
                    else:
                        logging.info("(This is a RE-connection. "
                                     "my salt is still {salt})".
                                     format(salt=self._random_salt))
                        hello_msg = messaging.M_C2S_HELLO_AGAIN(
                            self._random_salt, self._my_id, self._secret)

                    debug_print('about to send msg', str(hello_msg))
                    messaging.write_msg_to(self._server_socket, hello_msg)
                    '''2. get reply (expect welcome)'''
                    reply_msg = messaging.read_msg_from(
                        self._server_socket,
                        timeout=das_game_settings.client_handshake_timeout)
                    if messaging.is_message_with_header_string(reply_msg,
                                                               'S2C_REFUSE'):
                        debug_print('got refused by server_id {serv_id}'.
                                    format(serv_id=serv_id))
                        logging.info("Refused!")
                        continue
                    if not messaging.is_message_with_header_string(reply_msg,
                                                                   'S2C_WELCOME'):
                        logging.info(('CRASH or TIMEOUT for '
                                      'server_id {serv_id}').
                                     format(serv_id=serv_id))
                        raise RuntimeError('crash or timeout')
                    '''3. get my knight's ID'''
                    self._my_id = tuple(reply_msg.args[0])
                    self._secret = reply_msg.args[1]
                    logging.info(('Successful connection to Server_id '
                                  '{serv_id}. My knight ID is {kid}').
                                 format(serv_id=serv_id, kid=self._my_id))
                    '''4. wait for 1st game update'''
                    first_update =\
                        messaging.read_msg_from(
                            self._server_socket,
                            timeout=max(das_game_settings.max_done_wait,
                                        das_game_settings.
                                        client_handshake_timeout))
                    if not messaging.is_message_with_header_string(
                            first_update, 'UPDATE'):
                        logging.info(('Got {msg} but I expected my first '
                                      'update').format(msg=first_update))
                        raise RuntimeError('got' + str(first_update) +
                                           'instead of first update')

                    logging.info('Got my first update!')
                    '''5. try deserialize and extract game state'''
                    self._protected_game_state = protected.ProtectedDragonArena(
                        DragonArena.deserialize(first_update.args[1])
                    )
                    logging.info(('Successfully deserialized game state. '
                                  'Hash is {h}').format(
                        h=self._protected_game_state._dragon_arena.get_hash()))
                    return # exit the loop
                except Exception as e:
                    debug_print('CONNECTION WENT AWRY :(', e)
                    logging.info(('Connection went wrong! Reason: {e}'
                                ).format(e=str(e)))
            debug_print('failed to connect to everyone! D:')
            time.sleep(backoff)
            logging.info(('Backing off. Sleeping {sec}'
                        ).format(sec=backoff))
            debug_print('backing off...', backoff)
            backoff = sqrt(backoff * 1.7)

    @staticmethod
    def _ordered_server_list():
        server_addresses = das_game_settings.server_addresses  # long name
        rtts = [
            Client.measure_rtt_to(*addr)
            for addr in server_addresses
        ]
        # sort server addresses according to rtts.
        # Intentionally unstably sorted
        pairs = zip(rtts, range(len(server_addresses)))
        random.shuffle(pairs)
        ordered = [i for _, i in sorted(pairs, key= lambda x: x[0])]
        logging.info(('Server list in ascending ping... {ordered}'
                    ).format(ordered=ordered))
        return ordered

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
        logging.info(('Rtt to {ip} {port} was measured to be {rtt} sec'
                    ).format(ip=ip, port=port, rtt=rtt))
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
                    if das_game_settings.client_visualizer:
                        ascii_draw(new_state, me=self._my_id)
                    self._protected_game_state.replace_arena(new_state)
                    logging.info('Received a server update. Replaced arena')
                    debug_print('replaced arena! :D')
                    if new_state.game_over:
                        logging.info(('Latest game state is a GAME OVER '
                                      'state...'))
                        time.sleep(2.0)
                        logging.info(('Latest game state is a GAME OVER '
                                      'state...'))
                        print(('GAME OVER! {winners} win!'
                              ).format(winners=new_state.get_winner()))
                        logging.info(('GAME OVER! {winners} win!'
                                     ).format(winners=new_state.get_winner()))
                        os._exit(0)
            else:
                logging.info(('Incoming handler detected crash! '
                              'Re-establishing connection...'))
                self._connect_to_a_server(reconnect=True)
                logging.info('Connection back up!')
                # return

    def main_outgoing_loop(self):
        req_generator = self._player.main_loop(self._protected_game_state,
                                               self._my_id)
        debug_print('ready?')
        for request in req_generator:
            logging.info('Player yielded request: {request}'.
                         format(request=request))
            assert isinstance(request, Message)
            debug_print('forwarding', request)
            if not messaging.write_msg_to(self._server_socket, request):
                logging.info("Forwarding the player request has failed! "
                             "Incoming handler should fix this eventually..")
        debug_print('no more requests. Player closed down I guess')
        #TODO
