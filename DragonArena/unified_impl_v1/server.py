import threading
import time
import socket
import logging
import messaging
import random
import das_game_settings
from protected import ProtectedQueue
from messaging import Message, MessageError
from DragonArenaNew import DragonArena, Direction
from das_game_settings import debug_print
import hashlib
from math import pow
from drawing import ascii_draw

# #####################################
# SUBPROBLEMS START:


def ordering_func(reqs, tick_id):  # solved
    logging.info("Applying ORDERING function to ({num_reqs}) reqs.".format(
        num_reqs=len(reqs)))

    # First sort all reqs in place. Assumes that __lt__ and __eq__ are
    # implemented in the message object, and that their outcomes are
    # deterministic and hardware-independent.
    reqs.sort()

    # Now all servers would have the same sorted list to start with. This
    # list is then randomly shuffled in place using a shared seed so that the
    # that the order of how the messages are processed are unpredictable.

    random.seed(len(reqs) + tick_id)
    random.shuffle(reqs, lambda: random.random())

    return reqs


def _apply_and_log_all(dragon_arena, message_sequence):  # TODO
    # all requests are CLIENT action requests. no others.
    assert isinstance(dragon_arena, DragonArena)

    dragon_arena.increment_tick()

    for msg in message_sequence:
        if (not isinstance(msg, messaging.Message) or
            not msg.permitted_in_server_application_function()):
            logging.error(("Received and dropped message, "
                          "deemed inappropriate as a game request: {msg}"
                           ).format(msg=str(msg)))
            continue

        bad = False
        result = ""

        if msg.header_matches_string("R_MOVE"):
            if msg.args[0] == Direction.UP:
                result = dragon_arena.move_up(msg.sender)
            elif msg.args[0] == Direction.RIGHT:
                result = dragon_arena.move_right(msg.sender)
            elif msg.args[0] == Direction.DOWN:
                result = dragon_arena.move_down(msg.sender)
            elif msg.args[0] == Direction.LEFT:
                result = dragon_arena.move_left(msg.sender)
            else:
                bad = True
                result = "Bad move request."
        elif msg.header_matches_string("R_HEAL"):
            if dragon_arena.is_knight(tuple(msg.args[0])):
                result = dragon_arena.heal(tuple(msg.sender),
                                           tuple(msg.args[0]))
            else:
                bad = True
                result = "Bad heal request."
        elif msg.header_matches_string("R_ATTACK"):
            if dragon_arena.is_dragon(tuple(msg.args[0])):
                result = dragon_arena.attack(tuple(msg.sender),
                                             tuple(msg.args[0]))
            else:
                bad = True
                result = "Bad attack request."
        elif msg.header_matches_string("SPAWN"):
            assert isinstance(msg.sender, int)  # must be server id
            result = dragon_arena.spawn_knight(tuple(msg.args[0]))
        elif msg.header_matches_string("DESPAWN"):
            assert isinstance(msg.sender, int)  # must be server id
            k = tuple(msg.args[0])
            if dragon_arena._id_exists(k):
                if dragon_arena._is_alive(k):
                    logging.error(("Suppressing DESPAWN for knight {k}. "
                                  "Knight is already dead."
                                  ).format(k=k))
                    result = dragon_arena.kill_knight(k)
            else:
                bad = True
                result = "Id doesn't exist!"
        else:
            raise RuntimeError("chris fukt up damn")

        if bad:
            logging.error(("Message {msg} from {sender} was ignored. "
                          "Reason: {reason}").format(msg=str(msg),
                                                     sender=msg.sender,
                                                     reason=result))
        else:
            logging.error(("Message {msg} from {sender} was processed "
                          "successfully. DAS feedback: {reason}").format(
                msg=str(msg), sender=msg.sender, reason=result))
    #TODO LOG
    result = dragon_arena.let_dragons_attack()
    logging.info(result)
    logging.info(("ENTERING TICK {tick_id}").format(
        tick_id=dragon_arena.get_tick()))
#SUBPROBLEMS END:
##############################


def count_up_from(start):
    x = start
    try:
        while True:
            yield x
            x += 1
    except GeneratorExit:
        return


class ServerAcceptor:
    def __init__(self, port):
        assert type(port) is int and port > 0
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", port))
        self._sock.settimeout(None)
        self._sock.listen(das_game_settings.backlog)

    def shutdown(self):
        self._sock.close()
        debug_print('Acceptor shutting down!')

    def generate_incoming_sockets(self):
        try:
            while True:
                client_socket, addr = self._sock.accept()
                yield client_socket, addr
        except GeneratorExit:
            debug_print('acceptor generator killed')
            return
        except Exception as e:
            debug_print('Acceptor listening socket closed.')
            return

server_logging_chars = '"/:->$~."!+^cx*o'
class Server:
    @staticmethod
    def _my_logging_icon(server_id):
        c = server_logging_chars[server_id % len(server_logging_chars)]
        return c + c + c

    def __init__(self, server_id, is_starter):
        self._server_id = server_id
        self._is_starter = is_starter
        self._lagging_behind_serv_id = None
        assert 0 <= server_id < das_game_settings.num_server_addresses
        assert isinstance(is_starter, bool)
        log_filename = 'server_{s_id}.log'.format(s_id=server_id)
        logging.basicConfig(filename=log_filename,
                            filemode='a',
                            level=das_game_settings.logging_level,
                            format='%(asctime)s.%(msecs)03d srv '+
                                   '{: <3d}'.format(server_id) +
                                   Server._my_logging_icon(server_id)
                                   + ' %(message)s',
                            datefmt='%a %H:%M:%S')
        logging.info(("Server {server_id} started logging! :D"
                     ).format(server_id=server_id))
        # if I am crashing a lot in setup, do exponential backoff
        backoff_time = 0.01
        for try_index in count_up_from(0):
            logging.debug("try number {try_index}".
                          format(try_index=try_index))
            # TODO backoff time, try again when this throws exception
            try:
                self.try_setup()
            except Exception as e:
                logging.debug("  try number {try_index}".
                              format(try_index=try_index))
                debug_print('try setup exception. backing off', e)
                time.sleep(backoff_time)
                backoff_time = pow(backoff_time * 1.4, 0.8)
                continue
            self._kick_off_acceptor()
            self.main_loop()
            return

    def _active_server_ids(self):
        return [s_id for s_id, sock in self._active_servers()]

    def _lowest_id_connected_server(self):
        return min([self._server_id] + self._active_server_ids())

    def try_setup(self):
        """Will throw exceptions upwards if things fail"""
        debug_print('OK')
        debug_print('self._is_starter:', self._is_starter)
        if self._is_starter:
            debug_print('I am the starter:')
            logging.info("I am the starter!")
            self._dragon_arena = Server.create_fresh_arena()
            # self._tick_id() = 0
            self._server_sockets = \
                [None for _ in xrange(0, das_game_settings.
                                      num_server_addresses)]
        else:
            auth_sock, auth_index = self._connect_to_first_other_server()
            if auth_sock is None:
                raise RuntimeError(('I am not the starter! '
                                    'I need to wait for a starter'))
            logging.info("I am NOT the starter!".format())
            debug_print(auth_sock, auth_index)
            logging.info(("authority socket_index: {index}"
                         ).format(index=auth_index))
            debug_print('AUTHORITY SERVER:', auth_index)
            '''1. SYNC REQ ===> '''
            sync_req = messaging.M_S2S_SYNC_REQ(self._server_id, Server._server_secret(self._server_id))
            logging.info(("I am NOT the first server!. "
                          "Will sync with {auth_index}. "
                          "sending msg {sync_req}"
                          ).format(sync_req=sync_req,
                                   auth_index=auth_index))
            messaging.write_msg_to(auth_sock, sync_req)
            '''2. <=== SYNC REPLY '''
            sync_reply = messaging.read_msg_from(auth_sock, timeout=None)
            if messaging.is_message_with_header_string(sync_reply, 'S2S_SYNC_REPLY'):
                logging.info("Got expected S2S_SYNC_REPLY :)")
            else:
                logging.warning("Expected S2S_SYNC_REPLY, got {msg}".format(
                    msg=sync_reply))
                raise RuntimeError('expected sync reply! got ' +
                                   str(sync_reply))
            # self._tick_id() = sync_reply.args[0]
            try:
                self._dragon_arena = DragonArena.deserialize(sync_reply.args[1])
                logging.info("Got sync'd game state from server! hash: {h}".format(h=self._dragon_arena.get_hash()))
            except Exception as e:
                logging.warning(("Couldn't deserialize the given game state: {serialized_state}"
                             ).format(serialized_state=sync_reply.args[1]))
                raise RuntimeError('failed to serialize game state...', e)
            self._server_sockets = Server._socket_to_others({auth_index, self._server_id})

            hello_msg = messaging.M_S2S_HELLO(self._server_id, Server._server_secret(self._server_id))
            for server_id, sock in self._active_servers():
                if messaging.write_msg_to(sock, hello_msg):
                    logging.info(("Successfully HELLO'd server {server_id} with {hello_msg}"
                                 ).format(server_id=server_id,
                                          hello_msg=hello_msg))
                else:
                    logging.warning(("Couldn't HELLO server {server_id} with {hello_msg}. Must have crashed."
                                 ).format(server_id=server_id,
                                          hello_msg=hello_msg))
                    # server must have crashed in the meantime!
                    self._server_sockets[server_id] = None
                    continue
                welcome_msg = messaging.read_msg_from(sock, timeout=das_game_settings.S2S_wait_for_welcome_timeout)
                if messaging.is_message_with_header_string(welcome_msg, 'S2S_WELCOME'):
                    logging.info(("got expected WELCOME reply from {server_id}"
                                 ).format(server_id=server_id))
                else:
                    logging.info(("instead of WELCOME from {server_id}, got {msg}"
                                 ).format(server_id=server_id,
                                          msg=welcome_msg))
                    # server must have crashed in the meantime!
                    self._server_sockets[server_id] = None
            sync_done = messaging.M_S2S_SYNC_DONE()
            if messaging.write_msg_to(auth_sock, sync_done):
                logging.debug(("Sent {sync_done} to {auth_index}."
                              ).format(sync_done=sync_done, auth_index=auth_index))
            else:
                logging.warning(("Authority server has crashed OR "
                              "didn't wait for me before I could send {sync_done}"
                              ).format(sync_done=sync_done))
                raise RuntimeError('SYNC DONE didn`t succeed')
            self._server_sockets[auth_index] = auth_sock
            logging.debug(("Remembering socket for auth_server with id {auth_index}"
                         ).format(auth_index=auth_index))

        debug_print('WOOOHOOO READY')
        self._requests = ProtectedQueue()
        self._waiting_sync_server_tuples = ProtectedQueue()  #(msg.sender, socket)
        self._client_sockets = dict()
        self._knight_id_generator = self._knight_id_generator_func()
        self._server_client_load = [None for _ in range(das_game_settings.num_server_addresses)]
        self._server_client_load[self._server_id] = 0
        self._previous_hash = None
        self._servers_that_need_updating = set()

    def _knight_id_generator_func(self):
        assert isinstance(self._dragon_arena, DragonArena)
        sid = self._server_id # lambda would `enclose` the term 'self'
        my_knight_ids = filter(
            lambda k: k.get_identifier()[0] == sid,
            list(self._dragon_arena.get_knights())
        )
        my_knight_counters = map(lambda x: x[1], my_knight_ids)
        next_available_counter = (max(my_knight_counters) + 1
                                  if my_knight_counters
                                  else 0)

        logging.debug(("Prepared knight ID generator."
                      "Will count up from ({server_id},{next_knight_id})"
                      ).format(server_id=self._server_id,
                               next_knight_id=next_available_counter))
        try:
            for i in count_up_from(next_available_counter):
                yield (self._server_id, i)
        except GeneratorExit:
            debug_print('Cleaning up _knight_id_generator')
            return

    def _active_servers(self):
        try:
            for server_id, sock in enumerate(self._server_sockets):
                if sock is not None:
                    yield server_id, sock
        except GeneratorExit:
            return

    def _connect_to_first_other_server(self):
        for index, addr in enumerate(das_game_settings.server_addresses):
            if index == self._server_id:
                # skip myself
                continue
            sock = Server._try_connect_to(addr)
            if sock is not None:
                return sock, index
        return None, None

    @staticmethod
    def _socket_to_others(except_indices):
        f = lambda i: None if i in except_indices else Server._try_connect_to(das_game_settings.server_addresses[i])
        return list(map(f, xrange(0, das_game_settings.num_server_addresses)))

    @staticmethod
    def _try_connect_to(addr):  # addr == (ip, port)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1) # tweak this. 0.5 is plenty i think
            sock.connect(addr)
            logging.info("Successfully socketed to {addr}".format(addr=addr))
            return sock
        except:
            logging.warning("Failed to socket to {addr}".format(addr=addr))
            return None

    @staticmethod
    def create_fresh_arena():
        # ** unpacks dictionary as keyed arguments
        d = DragonArena(**das_game_settings.dragon_arena_init_settings)
        d.new_game()
        logging.info(("Created fresh arena  with settings {settings}, key {key} which hashes to {h}"
                     ).format(settings=das_game_settings.dragon_arena_init_settings,
                              key=d.key,
                              h=d.get_hash()))
        return d

    def _kick_off_acceptor(self):
        logging.debug(("acceptor started").format())
        my_port = das_game_settings.server_addresses[self._server_id][1]
        acceptor_handle = threading.Thread(
            target=Server._handle_new_connections,
            args=(self, my_port),
        )
        acceptor_handle.daemon = True
        acceptor_handle.start()

    def _handle_new_connections(self, port):
        logging.info(("acceptor handling new connections...").format())
        self._server_acceptor = ServerAcceptor(port)
        for new_socket, new_addr in self._server_acceptor.generate_incoming_sockets():
            debug_print('acceptor got', new_socket, new_addr)
            logging.info(("new acceptor connection from {addr}").format(addr=new_addr))
            #TODO handle the case that this new_addr is already associated with something
            babysitter_thread = threading.Thread(
                target=Server._babysit_newcomer_socket,
                args=(self, new_socket, new_addr),
            )
            babysitter_thread.daemon = True
            babysitter_thread.start()

    def _babysit_newcomer_socket(self, sock, addr):
        logging.debug(("handling messages from newcomer socket at {addr}"
                     ).format(addr=addr))
        # TODO I would love to make this a generator. But it seems that it doesnt EXIT like it should
        # generator = messaging.generate_messages_from(socket,timeout=None)
        while True:
            msg = messaging.read_msg_from(sock, timeout=None)
        # for msg in generator:
            logging.debug(("newcomer socket sent {msg}").format(msg=str(msg)))
            if msg is MessageError.CRASH:
                debug_print('newcomer socket died in the cradle :(. Hopefully just a ping. killing incoming reader daemon')
                return
            debug_print('_handle_socket_incoming yielded', msg)
            if msg.header_matches_string("C2S_HELLO"):
                self._handle_client_join(msg, sock, addr, hello_again=False)
            elif msg.header_matches_string("C2S_HELLO_AGAIN"):
                self._handle_client_join(msg, sock, addr, hello_again=True)
            elif msg.header_matches_string('S2S_HELLO'):
                received_secret = msg.args[0]
                derived_secret = Server._server_secret(msg.sender)
                if received_secret == derived_secret:
                    logging.info(("Got a good HELLO handshake from {server_id} "
                                  "and secret {derived_secret}. Adding socket"
                                  ).format(server_id=msg.sender,
                                           derived_secret=derived_secret))
                    debug_print('server is up! synced by someone else server!')
                    self._server_sockets[msg.sender] = sock
                    messaging.write_msg_to(sock, messaging.M_S2S_WELCOME(self._server_id))
                else:
                    logging.warning(("Got a HELLO handshake from {server_id} "
                                  "but their secret {received_secret} mismatched "
                                  "mine {derived_secret}. Refusing"
                                  ).format(server_id=msg.sender,
                                           received_secret=received_secret,
                                           derived_secret=derived_secret))
                    messaging.write_msg_to(sock, messaging.M_REFUSE())
                return
            elif msg.msg_header == messaging.header2int['S2S_SYNC_REQ']:
                received_secret = msg.args[0]
                derived_secret = Server._server_secret(msg.sender)
                if received_secret == derived_secret:
                    logging.info(("This is server {s_id} that wants to sync! "
                                  "Secrets matched with {received_secret}. "
                                  "Killing incoming handler. Setting FLAG for tick thread."
                                  ).format(s_id=msg.sender,
                                           received_secret=received_secret))
                    self._waiting_sync_server_tuples.enqueue((msg.sender, sock))
                    debug_print('newcomer handler exiting')
                else:
                    logging.warning(("SYNC message got from `{s_id}`. However, "
                                  "their secret {received_secret} mismatches "
                                  "mine {derived_secret}"
                                  ).format(s_id=msg.sender))
                    debug_print('newcomer handler exiting')
                    messaging.write_msg_to(sock, messaging.M_REFUSE())
                return

    def _handle_client_join(self, msg, sock, addr, hello_again):

        # NOTE knight_id analagous to player_id
        if self._i_should_refuse_clients():
            messaging.write_msg_to(sock, messaging.M_REFUSE())
            logging.warning(("Refused a client at {addr} "
                          "Server loads are currently approx. {loads}."
                          "Client wanted to rejoin: {rejoin}"
                          ).format(addr=addr,
                                   loads=self._server_client_load,
                                   rejoin=hello_again))
            return
        if not hello_again:
            # New client! generate new knight
            player_id = next(self._knight_id_generator)
            logging.info(("Generated player/knight ID {player_id} "
                          "for the new client."
                          ).format(player_id=player_id))
            spawn_msg = messaging.M_SPAWN(self._server_id, player_id)
            self._requests.enqueue(spawn_msg)
            logging.info(("Enqueued spawn request {spawn_msg} "
                          "for the new client."
                          ).format(spawn_msg=spawn_msg))
            derived_secret = Server._client_secret(addr[0], tuple(player_id),
                                                   msg.args[0],
                                                   self._dragon_arena.key)
        else:
            # Reconnecting client
            debug_print('returning client!')
            salt = msg.args[0]
            player_id = tuple(msg.args[1])
            received_secret = msg.args[2]
            derived_secret = Server._client_secret(addr[0], tuple(player_id),
                                                   salt,
                                                   self._dragon_arena.key)
            if received_secret != derived_secret:
                debug_print('secret mismatch!')
                logging.warning(("Refused a client`s reconnection. Received sescret {received_secret}, "
                              "but should have been {derived_secret}."
                              ).format(derived_secret=derived_secret,
                                       received_secret=received_secret))
                messaging.write_msg_to(sock, messaging.M_REFUSE())
                return
            logging.info(("Client successfully reconnected with secret {received_secret}."
                          ).format(received_secret=received_secret))

        # reconnecting or not...
        welcome = messaging.M_S2C_WELCOME(self._server_id, player_id,
                                          derived_secret)
        messaging.write_msg_to(sock, welcome)
        debug_print(('welcomed client/knight {player_id} to the game'
                    ).format(player_id=player_id))
        self._client_sockets[addr] = sock
        self._handle_client_incoming(sock, addr, player_id)
        return

    def _handle_client_incoming(self, sock, addr, player_id):
        #TODO this function gets as param the player's knight ID
        #TODO before submitting it as a request, this handler wi
        debug_print('client handler!')
        # for msg in messaging.generate_messages_from(socket, timeout=None):
        while True:
            msg = messaging.read_msg_from(sock, timeout=None)
            debug_print('client sumthn')
            if msg == MessageError.CRASH:
                debug_print('client crashed!')
                logging.warning(("Incoming daemon noticed client at {addr} crashed."
                              "Removing client"
                              ).format(addr=addr))
                self._requests.enqueue(messaging.M_DESPAWN(self._server_id,
                                                           player_id))
                self._client_sockets.pop(addr)
                #TODO debug why a client cannot REJOIN
                break
            #TODO overwrite the SENDER field. this is needed for logging AND to make sure the request is valid
            msg.sender = player_id # Server annotates this to ensure client doesnt doctor their packets
            debug_print('client incoming', msg)
            self._requests.enqueue(msg)
            logging.debug(("Got client incoming {msg}!").format(msg=str(msg)))
            pass
        debug_print('client handler dead :(')

    @staticmethod
    def _server_secret(server_id):
        m = hashlib.md5(str(server_id))
        m = hashlib.md5(das_game_settings.server_secret_salt)
        return m.hexdigest()[:12]

    @staticmethod
    def _client_secret(ip, player_id, client_random_salt, dragon_arena_key):
        m = hashlib.md5()
        m.update(str(ip))
        m.update(str(player_id))
        m.update(str(client_random_salt))
        m.update(str(dragon_arena_key))
        return m.hexdigest()[:10]

    def main_loop(self):
        logging.info("Main loop started. tick_id is {tick_id}".
                     format(tick_id=self._tick_id()))
        debug_print('MAIN LOOP :)')
        while True:
            tick_start = time.time()
            debug_print('tick', self._tick_id())
            logging.debug(("At loop start, DA hashes to {h}"
                         ).format(h=self._dragon_arena.get_hash()))

            '''SWAP BUFFERS'''
            my_req_pool = self._requests.drain_if_probably_something()
            logging.debug(("drained ({num_reqs}) requests in tick {tick_id}"
                         ).format(num_reqs=len(my_req_pool),
                                  tick_id=self._tick_id()))
            '''FLOOD REQS'''
            self._step_flood_reqs(my_req_pool)

            # synchee_tuple is server getting synched
            # this variable is of the form (server_id, socket)
            debug_print('to sync:', self._waiting_sync_server_tuples._q )
            synchee_tuple = self._waiting_sync_server_tuples.dequeue(timeout=0.3)
            logging.debug(("lowest id {lowest}. ").format(lowest=self._lowest_id_connected_server()))
            if synchee_tuple is not None and self._server_id != self._lowest_id_connected_server():
                # some server has entered the ring with a lower ID!
                # They are the syncher, not me
                # Remove and kill all connected waiting synchees.
                # they will find the new syncher when they retry
                sync_drained = self._waiting_sync_server_tuples.drain()
                logging.info(("Wanted to sync, but {lowest} ID is responsible!. "
                              "Drained and killed stored sync sockets for ids: {sync_set}."
                              "Suppressing DONE step"
                              ).format(sync_set={x[0] for x in sync_drained} | {synchee_tuple[0]},
                                       lowest=self._lowest_id_connected_server()))
                synchee_tuple[1].close()
                synchee_tuple = None
                for tup in sync_drained:
                    tup[1].close()
            debug_print('synchee_tuple', synchee_tuple)
            if synchee_tuple is not None:
                debug_print(('---eyyy Server {x} wants to sync!---'
                            ).format(x=synchee_tuple[0]))
                # collect DONES before sending your own
                logging.info(("Ticker thread saw FLAG! server {server_id} waiting to sync! LEADER tick."
                              "Suppressing DONE step"
                              ).format(server_id=synchee_tuple[0]))
                '''READ REQS AND WAIT'''
                my_req_pool.extend(self._step_read_reqs_and_wait(update_enabled=False))
                '''SORT REQ SEQUENCE'''
                req_sequence = ordering_func(my_req_pool, self._tick_id())
                self._previous_hash = self._dragon_arena.get_hash() # Need for updatin <#>2/4
                logging.debug(("Storing hash {h} before I transition into next "
                              "tick. This is now the `previous hash`"
                              ).format(h=self._previous_hash))
                '''APPLY AND LOG'''
                _apply_and_log_all(self._dragon_arena, req_sequence)
                '''### SPECIAL SYNC STEP ###''' # returns when sync is complete
                self._step_sync_server(*synchee_tuple)
                logging.info(("Sync finished. Releasing DONE flood for tick {tick_id}"
                             ).format(tick_id=self._tick_id()))
                '''<<STEP FLOOD DONE>>'''
                self._step_flood_done(except_server_id=synchee_tuple[0],
                                        tick_count_modifier=-1)

            else: #NO SERVERS WAITING TO SYNC
                # send own DONES before collecting those of others
                logging.info(("No servers waiting to sync. Normal tick. Flooding done.").format())
                '''<<STEP FLOOD DONE>>'''
                self._step_flood_done(except_server_id=None)
                '''READ REQS AND WAIT'''
                my_req_pool.extend(self._step_read_reqs_and_wait(update_enabled=True))
                '''SORT REQ SEQUENCE'''
                req_sequence = ordering_func(my_req_pool, self._tick_id())
                '''APPLY AND LOG'''
                self._previous_hash = self._dragon_arena.get_hash() # Need for updating # <#>2/4
                logging.debug(("Storing hash {h} before I transition into next "
                              "tick. This is now the `previous hash`"
                              ).format(h=self._previous_hash))
                _apply_and_log_all(self._dragon_arena, req_sequence)


            logging.debug(("Before updating, DA hashes to {h}"
                         ).format(h=self._dragon_arena.get_hash()))

            if das_game_settings.server_visualizer:
                ascii_draw(self._dragon_arena)
            '''UPDATE CLIENTS'''
            self._step_update_clients()
            '''UPDATE SERVERS'''
            if self._servers_that_need_updating:
                # I decided these people are behind. so lets update them <#>3/4
                s2s_update_msg = messaging.M_S2S_UPDATE(self._server_id,
                                                self._tick_id(),
                                                self._dragon_arena.serialize(),
                                                self._previous_hash)

                for server_id in self._servers_that_need_updating:
                    logging.info(("Sent S2S_UPDATE to {server_id}. attaching previous hash {h}"
                                  ).format(server_id=server_id,
                                           h=self._previous_hash))
                    messaging.write_msg_to(self._server_sockets[server_id], s2s_update_msg)
            self._servers_that_need_updating.clear()


            '''SLEEP STEP'''
            # TODO put back in later
            if self._waiting_sync_server_tuples.poll_nonempty():
                logging.info(("Some servers want to sync! no time to sleep on tick {tick_id}"
                             ).format(tick_id=self._tick_id()))
            else:
                sleep_time = das_game_settings.server_min_tick_time - (time.time() - tick_start)
                if sleep_time > 0.0:
                    logging.info(("Sleeping for ({sleep_time}) seconds for tick_id {tick_id}"
                                 ).format(sleep_time=sleep_time, tick_id=self._tick_id()))
                    time.sleep(sleep_time)
                else:
                    logging.info(("No time for sleep for tick_id {tick_id}"
                                 ).format(tick_id=self._tick_id()))

    def _i_should_refuse_clients(self):
        if self._dragon_arena.game_is_full():
            return True
        for server_id, sock in enumerate(self._server_sockets):
            if sock is None:
                 self._server_client_load[server_id] = None
        my_load = len(self._client_sockets)
        self._server_client_load[self._server_id] = my_load
        total_active_loads = filter(lambda x: x is not None,
                                    self._server_client_load)
        total_num_servers = len(total_active_loads)
        if total_num_servers == 1:
            debug_print('there is no other server!')
            return False
        if my_load < max(0, das_game_settings.min_server_client_capacity):
            debug_print('I can certainly take more')
            return False

        total_loads = sum(total_active_loads)

        assert isinstance(total_loads, int)

        average_server_load = \
            total_loads / float(total_num_servers)
        return my_load > (average_server_load *
                          das_game_settings.server_overcapacity_ratio)

    def _active_server_indices(self):
        return filter(
            lambda x: self._server_sockets[x] is not None,
            range(das_game_settings.num_server_addresses),
        )

    def _step_flood_reqs(self, my_req_pool):
        for serv_id, sock in enumerate(self._server_sockets):
            if sock is None:
                logging.debug(("Skipping req flood to server_id {serv_id} (No socket)"
                              ).format(serv_id=serv_id))
                continue
            try:
                messaging.write_many_msgs_to(sock, my_req_pool)
                logging.debug(("Finished flooding reqs to serv_id {serv_id}"
                               ).format(serv_id=serv_id))
            except:
                 logging.warning(("Flooding reqs to serv_id {serv_id} crashed!"
                               ).format(serv_id=serv_id))

    def _step_flood_done(self, except_server_id=None, tick_count_modifier=0):
        logging.warning(("DONE flood. actual tick {tick_id}. but DONES will say its {modified}"
                     ).format(tick_id=self._tick_id(),
                              modified=self._tick_id() + tick_count_modifier))
        # need to specify except_server_ids of newly-synced server. this prevents them from getting an extra DONE
        if self._tick_id() % das_game_settings.ticks_per_game_hash == 0:
            logging.warning("This is a hashing tick!!")
            done_msg = messaging.M_DONE_HASHED(self._server_id,
                                                self._tick_id() + tick_count_modifier,
                                                len(self._client_sockets),
                                                self._dragon_arena.get_hash())
        else:
            done_msg = messaging.M_DONE(self._server_id,
                             self._tick_id() + tick_count_modifier,
                             len(self._client_sockets))
        '''SEND DONE'''

        logging.info(("Releasing barrier of {tick_id} for {whom}"
                     ).format(tick_id=self._tick_id(),
                              whom=self._active_server_indices()))
        for server_id in self._active_server_indices():
            if server_id is except_server_id:
                logging.debug(("Suppressing {server_id}'s DONE message."
                              "It was newly synced and wasn't part of the barrier."
                              ).format(server_id=server_id))
                continue
            sock = self._server_sockets[server_id]
            if messaging.write_msg_to(sock, done_msg):
                logging.debug(("sent DONE {done_msg} for tick_id {tick_id} to server_id {server_id}"
                             ).format(done_msg=done_msg,
                                      tick_id=self._tick_id(),
                                      server_id=server_id))
         #Note. crash in this loop leads other servers to arrive at inconsistent state

    def _step_read_reqs_and_wait(self,update_enabled=True):
        res = []
        active_indices = self._active_server_indices()
        logging.info(("AT BARRIER in tick {tick_id}. waiting for servers {active_indices}"
                     ).format(tick_id=self._tick_id(),
                            active_indices=active_indices))
        debug_print('other servers:', self._server_sockets)

        # Need to lock down the servers I am waiting for. SYNCED servers might join inbetween
        waiting_for = list(self._active_servers())
        debug_print('waiting for ', waiting_for)

        for server_id, sock in waiting_for:
            res.extend(self._read_and_wait_for(server_id, sock,update_enabled=update_enabled))

        debug_print('server load', self._server_client_load[self._server_id])
        logging.debug("Released from the barrier for tick_id {tick_id}".format(tick_id=self._tick_id()))
        debug_print("!!!RELEASED FROM TICK", self._tick_id())
        logging.debug(("Starting tick {tick_id}").format(tick_id=self._tick_id()))
        return res

    def _read_and_wait_for(self, server_id, sock, update_enabled=True):
        temp_batch = []
        debug_print('expecting done from ', server_id)
        while True:
            msg = messaging.read_msg_from(sock, timeout=das_game_settings.max_done_wait)
            if not isinstance(msg, Message):
                if msg is MessageError.CRASH:
                    logging.warning(("Wait&recv for {server_id} ended in CRASH"
                                 ).format(server_id=server_id))
                else:
                    logging.warning(("Wait&recv for {server_id} ended in TIMEOUT"
                                  "(might be a deadlock?)"
                                 ).format(server_id=server_id))
                debug_print('Lost connection!')
                # Clean up, discard temp_batch
                self._server_sockets[server_id] = None
                return []
            if msg.header_matches_string('DONE'):
                debug_print('got a DONE')
                # DONE got. accept the batch. No hash here.
                return temp_batch
            elif msg.header_matches_string('DONE_HASHED'):
                other_tick_id = msg.args[0]
                self._server_client_load[server_id] = msg.args[1]
                debug_print('got a DONE_HASHED')
                if update_enabled and self._sender_needs_update(msg, server_id):
                    # This server is behind! Make a note for later! <#>1/4
                    self._servers_that_need_updating.add(server_id)
                # DONE got. accept the batch
                return temp_batch
            elif msg.header_matches_string('S2S_UPDATE'):
                # sender thinks I need this update! <#>4/3
                self._handle_S2S_update(msg, server_id)
            else:
                # some request message. Store and keep going
                temp_batch.append(msg)



    def _sender_needs_update(self, done_msg, other_server_id):
        other_tick_id = done_msg.args[0]
        t = self._tick_id()
        if other_tick_id < t:
            #They are behind!
            logging.error(("Noticed {other_server_id} is in tick "
                          "{other_tick_id} and I am in {my_tick_id}. Will send UPDATE"
                         ).format(other_server_id=other_server_id,
                                  other_tick_id=other_tick_id,
                                  my_tick_id=t))
            return True
        if other_tick_id > t:
            #They are ahead! I need an update! I hope they notice
            logging.warning(("Noticed server {other_server_id} is ahead in "
                          "tick {other_tick_id} while I am in {my_tick_id}. "
                          "Hope they send an UPDATE"
                          ).format(other_server_id=other_server_id,
                                  other_tick_id=other_tick_id,
                                  my_tick_id=t))
            return False
        other_hash = done_msg.args[2]
        my_hash = self._dragon_arena.get_hash()
        if other_hash < my_hash:
            logging.error(("Noticed {other_server_id} has game hash "
                          "{other_hash}, while I have {my_hash} "
                          "in tick {my_tick_id}. Will send UPDATE."
                          ).format(other_server_id=other_server_id,
                                  other_hash=other_hash,
                                  my_hash=my_hash,
                                  my_tick_id=t))
            return True

        logging.debug(("Noticed nothing unusual about the DONE_HASHED from "
                      "{other_server_id} and tick {my_tick_id}"
                      ).format(other_server_id=other_server_id,
                               my_tick_id=t))
        return False

    def _handle_S2S_update(self, msg, other_server_id):
        # NOTE this update is from the current tick,
        # but you are comparing YOUR previous hash to their previous hash
        # Other server sent me an update! Lets see if I can benefit...
        other_tick_id = msg.args[0]
        if other_tick_id < self._tick_id:
            logging.warning(("I got an UPDATE from server {other_server_id} "
                          "with tick ID {other_tick_id}. But I am in "
                          "tick {tick_id}, so I'll discard it."
                         ).format(other_server_id=other_server_id,
                                  other_tick_id=other_tick_id,
                                  tick_id=self._tick_id()))
            return
        try:
            other_state = DragonArena.deserialize(msg.args[1])
        except Exception as e:
            logging.error(("Failed to make sense of S2S_UPDATE "
                          "from {other_server_id}. Discarding."
                         ).format(other_server_id=other_server_id))
            debug_print("FAILED TO DESER S2S UPDATE")
            return
        if other_tick_id > self._tick_id:
            logging.info(("I got an UPDATE from server {other_server_id} "
                          "with tick ID {other_tick_id}. I am in "
                          "tick {tick_id}, so I'll accept it."
                         ).format(other_server_id=other_server_id,
                                  other_tick_id=other_tick_id,
                                  tick_id=self._tick_id()))
            self._dragon_arena = other_state
            return
        their_prev_hash = msg.args[2]
        my_prev_hash = self._previous_hash
        if their_prev_hash > my_prev_hash:
            logging.info(("I got an UPDATE from server {other_server_id} "
                          "with tick ID {other_tick_id} (same as me). "
                          "Their prev hash {their_prev_hash} > {my_prev_hash}, so I'll accept it."
                         ).format(other_server_id=other_server_id,
                                  other_tick_id=other_tick_id,
                                  their_prev_hash=their_prev_hash,
                                  my_prev_hash=my_prev_hash))
            self._dragon_arena = other_state


    def _tick_id(self):
        return self._dragon_arena.get_tick()

    def _step_sync_server(self, synchee_id, socket):
        update_msg = messaging.M_S2S_SYNC_REPLY(self._tick_id(),
                                                self._dragon_arena.serialize())
        logging.debug(("Sync REPLY DA hashes to {h}"
                     ).format(h=self._dragon_arena.get_hash()))
        if socket is None:
            return
        debug_print('syncing:', synchee_id, socket)
        if not messaging.write_msg_to(socket, update_msg):
            debug_print('failed to send sync msg')
            logging.warning(("Failed to send sync msg to waiting server "
                          "{synchee_id}").format(synchee_id=synchee_id))
            return

        logging.info(("Sent sync msg to waiting server "
                      "{synchee_id}").format(synchee_id=synchee_id))
        debug_print('awaiting SYNC DONE from ',synchee_id,'...')
        logging.info(("awaiting SYNC DONE from {synchee_id}...  "
                      ).format(synchee_id=synchee_id))
        sync_done = messaging.read_msg_from(socket, timeout=das_game_settings.max_server_sync_wait)
        if messaging.is_message_with_header_string(sync_done, 'S2S_SYNC_DONE'):
            logging.info(("Got {msg} from sync server {synchee_id}! "
                          ":)").format(msg=sync_done, synchee_id=synchee_id))
            debug_print('SYNCED',synchee_id,'YA, BUDDY :)')
            self._server_sockets[synchee_id] = socket
            logging.debug(("Spawned incoming handler for "
                          "newly-synced server {synchee_id}"
                         ).format(synchee_id=synchee_id))
        else:
            debug_print('either timed out or crashed. either way, disregarding')
            logging.warning(("Hmm. It seems that {synchee_id} has"
                          "crashed before syncing. Oh well :/"
                         ).format(synchee_id=synchee_id))

    def _step_update_clients(self):
        update_msg = messaging.M_UPDATE(self._server_id, self._tick_id(), self._dragon_arena.serialize())
        logging.debug(("Update msg ready for tick {tick_id}"
                     ).format(tick_id=self._tick_id()))
        logging.info(("Client set for tick {tick_id}: {clients}"
                     ).format(tick_id=self._tick_id(), clients=self._client_sockets.keys()))
        debug_print('CLIENT SOCKS', self._client_sockets)
        for addr, sock in self._client_sockets.iteritems():
            #TODO investigate why addr is an ip and not (ip,port)
            if messaging.write_msg_to(sock, update_msg):
                debug_print('updated client', addr)
                logging.debug(("Successfully updated client at addr {addr}"
                              "for tick_id {tick_id}"
                              ).format(addr=addr,
                                       tick_id=self._tick_id()))
            else:
                logging.warning(("Failed to update client at addr {addr}"
                              "for tick_id {tick_id}"
                              ).format(addr=addr,
                                       tick_id=self._tick_id()))
                self._client_sockets.pop(addr)
        logging.info(("All updates done for tick_id {tick_id}"
                     ).format(tick_id=self._tick_id()))
        if self._dragon_arena.game_over:
            debug_print('GAME OVER!')
            self._server_acceptor.shutdown()
            logging.critical(("GAME OVER! {winners} win! Acceptor shutdown. "
                         "Server shutting down..."
                         ).format(winners=self._dragon_arena.get_winner()))
            time.sleep(das_game_settings.max_server_sync_wait)
            exit(0)
