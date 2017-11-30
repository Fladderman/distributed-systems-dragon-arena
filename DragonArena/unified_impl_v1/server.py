import threading
import time
import socket
import sys
import os
import logging
import messaging
import random
import das_game_settings
import protected
from messaging import Message, MessageError
from DragonArenaNew import Creature, Knight, Dragon, DragonArena
from das_game_settings import debug_print
import hashlib

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
        assert isinstance(msg, messaging.Message)

        # valid = msg.permitted_in_server_application_function() and ``correct sender``

        bad = False
        result = ""

        if msg.header_matches_string("R_MOVE"):
            if msg.args[0] == 'u':
                result = dragon_arena.move_up(msg.sender)
            elif msg.args[0] == 'r':
                result = dragon_arena.move_right(msg.sender)
            elif msg.args[0] == 'd':
                result = dragon_arena.move_down(msg.sender)
            elif msg.args[0] == 'l':
                result = dragon_arena.move_left(msg.sender)
            else:
                bad = True
                result = "Bad move request."
        elif msg.header_matches_string("R_HEAL"):
            if dragon_arena.is_knight(tuple(msg.args[0])):
                result = dragon_arena.heal(tuple(msg.sender), tuple(msg.args[0]))
            else:
                bad = True
                result = "Bad heal request."
        elif msg.header_matches_string("R_ATTACK"):
            if dragon_arena.is_dragon(tuple(msg.args[0])):
                result = dragon_arena.attack(tuple(msg.sender), tuple(msg.args[0]))
            else:
                bad = True
                result = "Bad attack request."
        elif msg.header_matches_string("SPAWN"):
            assert isinstance(msg.sender, int)  # must be server id
            result = dragon_arena.spawn_knight(tuple(msg.args[0]))
        elif msg.header_matches_string("DESPAWN"):
            assert isinstance(msg.sender, int)  # must be server id
            k = tuple(msg.args[0])
            if dragon_arena._is_alive(k):
                logging.info(("Suppressing DESPAWN for knight {k}. "
                              "Knight is already dead."
                              ).format(k=k))
                result = dragon_arena.kill_knight(k)
        else:
            raise "chris fukt up damn"

        if bad:
            logging.info(("Message {msg} from {sender} was ignored. "
                          "Reason: {reason}").format(msg=str(msg),
                                                     sender=msg.sender,
                                                     reason=result))
        else:
            logging.info(("Message {msg} from {sender} was processed "
                          "successfully. DAS feedback: {reason}").format(
                msg=str(msg), sender=msg.sender, reason=result))
    #TODO LOG
    result = dragon_arena.let_dragons_attack()
    logging.info(("Player actions successfully processed for tick {tick_id}"
                 ).format(tick_id=dragon_arena.get_tick()))
    logging.info(result)
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

    def generate_incoming_sockets(self):
        try:
            while True:
                client_socket, addr = self._sock.accept()
                yield client_socket, addr
        except GeneratorExit:
            debug_print('acceptor generator killed')
            return

class Server:
    def __init__(self, server_id):
        log_filename = 'server_{s_id}.log'.format(s_id=server_id)
        logging.basicConfig(filename=log_filename, filemode='w', level=logging.INFO)
        logging.info(("==========================\n"
                      "Server {server_id} started logging at {time}\n"
                      "=========================="
                      ).format(server_id=server_id, time=time.time()))
        self._server_id = server_id
        # if I am crashing a lot in setup, do exponential backoff
        backoff_time = das_game_settings.max_server_sync_wait
        for try_index in count_up_from(0):
            logging.info("try number {try_index}".format(try_index=try_index))
            # TODO backoff time, try again when this throws exception
            try:
                self.try_setup()
            except Exception as e:
                logging.info("  try number {try_index}".format(try_index=try_index))
                debug_print('try setup exception. backing off', e)
                time.sleep(backoff_time)
                backoff_time *= 2
                continue
            self._kick_off_acceptor()
            self.main_loop()
            return

    def try_setup(self):
        '''Will throw exceptions upwards if things fail'''
        debug_print('OK')
        auth_sock, auth_index = self._connect_to_first_other_server()
        debug_print(auth_sock, auth_index)
        logging.info("authority socket_index: {index}".format(
            index=auth_index))
        if auth_sock is None:
            # I am first! :D
            debug_print('I AM THE FIRST SERVER:', auth_index)
            logging.info("I am the first server!".format())
            self._dragon_arena = Server.create_fresh_arena()
            # self._tick_id() = 0
            self._server_sockets = \
                [None for _ in xrange(0, das_game_settings.
                                      num_server_addresses)]
        else:
            # I'm not first :[
            debug_print('AUTHORITY SERVER:', auth_index)
            '''1. SYNC REQ ===> '''
            sync_req = messaging.M_S2S_SYNC_REQ(self._server_id)
            logging.info(("I am NOT the first server!. "
                          "Will sync with auth_index. "
                          "sending msg {sync_req}").format(sync_req=sync_req))
            messaging.write_msg_to(auth_sock, sync_req)
            '''2. <=== SYNC REPLY '''
            sync_reply = messaging.read_msg_from(auth_sock, timeout=None)
            logging.info("Got sync reply: {reply}".format(
                reply=str(sync_reply)))
            if messaging.is_message_with_header_string(sync_reply, 'S2S_SYNC_REPLY'):
                logging.info("Got expected S2S_SYNC_REPLY :)")
            else:
                logging.info("Expected S2S_SYNC_REPLY, got {msg}".format(
                    msg=sync_reply))
                raise RuntimeError('expected sync reply! got ' + str(msg))
            # self._tick_id() = sync_reply.args[0]
            try:
                self._dragon_arena = DragonArena.deserialize(sync_reply.args[1])
                logging.info(("Got sync'd game state from server! serialized: {serialized_state}"
                             ).format(serialized_state=sync_reply.args[1]))
            except Exception as e:
                logging.info(("Couldn't deserialize the given game state: {serialized_state}"
                             ).format(serialized_state=sync_reply.args[1]))
                raise RuntimeError('failed to serialize game state...', e)
            self._server_sockets = Server._socket_to_others({auth_index, self._server_id})

            hello_msg = messaging.M_S2S_HELLO(self._server_id)
            for server_id, sock in self._active_servers():
                if messaging.write_msg_to(sock, hello_msg):
                    logging.info(("Successfully HELLO'd server {server_id} with {hello_msg}"
                                 ).format(server_id=server_id,
                                          hello_msg=hello_msg))
                else:
                    logging.info(("Couldn't HELLO server {server_id} with {hello_msg}. Must have crashed."
                                 ).format(server_id=server_id,
                                          hello_msg=hello_msg))
                    # server must have crashed in the meantime!
                    self._server_sockets[server_id] = None
                    continue
                welcome_msg = messaging.read_msg_from(sock,timeout=das_game_settings.S2S_wait_for_welcome_timeout)
                if messaging.is_message_with_header_string(welcome_msg, 'S2S_WELCOME'):
                    logging.info(("got expected WELCOME reply from {server_id}"
                                 ).format(server_id=server_id))
                else:
                    logging.info(("instead of WELCOME from {server_id}, got {msg}"
                                 ).format(server_id=server_id,
                                          msg=reply2))
                    # server must have crashed in the meantime!
                    self._server_sockets[server_id] = None
            sync_done = messaging.M_S2S_SYNC_DONE()
            if messaging.write_msg_to(auth_sock, sync_done):
                logging.info(("Sent {sync_done} to {auth_index}."
                              ).format(sync_done=sync_done, auth_index=auth_index))
            else:
                logging.info(("Authority server has crashed OR "
                              "didn't wait for me before I could send {sync_done}"
                              ).format(sync_done=sync_done))
                raise RuntimeError('SYNC DONE didn`t succeed')
            self._server_sockets[auth_index] = auth_sock
            logging.info(("Remembering socket for auth_server with id {auth_index}"
                         ).format(auth_index=auth_index))

        debug_print('WOOOHOOO READY')
        self._requests = protected.ProtectedQueue()
        self._waiting_sync_server_tuples = protected.ProtectedQueue() #(msg.sender, socket)
        self._client_sockets = dict()
        self._knight_id_generator = self._knight_id_generator_func()
        self._server_client_load = [None for _ in range(das_game_settings.num_server_addresses)]


    def _knight_id_generator_func(self):
        my_knight_ids = filter(
            lambda x: x[0]==self._server_id,
            list(self._dragon_arena.get_knights())
        )
        my_knight_counters = map(lambda x: x[1], my_knight_ids)
        next_available_counter = (max(my_knight_counters) + 1
                                  if my_knight_counters
                                  else 0)

        logging.info(("Prepared knight ID generator."
                      "Will count up from ({server_id},{next_knight_id})"
                      ).format(server_id=self._server_id,
                               next_knight_id=next_available_counter))
        try:
            for i in count_up_from(next_available_counter + 1):
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
    def _try_connect_to(addr): #addr == (ip, port)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1) # tweak this. 0.5 is plenty i think
            sock.connect(addr)
            logging.info(("Successfully socketed to {addr}").format(addr=addr))
            return sock
        except:
            logging.info(("Failed to socket to {addr}").format(addr=addr))
            return None

    @staticmethod
    def create_fresh_arena():
        # ** unpacks dictionary as keyed arguments
        d = DragonArena(**das_game_settings.dragon_arena_init_settings)
        d.new_game()
        logging.info(("Created fresh arena  with settings {settings} and key {key}"
                     ).format(settings=das_game_settings.dragon_arena_init_settings,
                              key=d.key))
        return d

    def _kick_off_acceptor(self):
        logging.info(("acceptor started").format())
        my_port = das_game_settings.server_addresses[self._server_id][1]
        acceptor_handle = threading.Thread(
            target=Server._handle_new_connections,
            args=(self, my_port),
        )
        acceptor_handle.daemon = True
        acceptor_handle.start()

    def _handle_new_connections(self, port):
        logging.info(("acceptor handling new connections...").format())
        server_acceptor = ServerAcceptor(port)
        for new_socket, new_addr in server_acceptor.generate_incoming_sockets():
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
        logging.info(("handling messages from newcomer socket at {addr}"
                     ).format(addr=addr))
        # TODO I would love to make this a generator. But it seems that it doesnt EXIT like it should
        # generator = messaging.generate_messages_from(socket,timeout=None)
        while True:
            msg = messaging.read_msg_from(sock, timeout=None)
        # for msg in generator:
            logging.info(("newcomer socket sent {msg}").format(msg=str(msg)))
            if msg is MessageError.CRASH:
                debug_print('newcomer socket died in the cradle :(. Hopefully just a ping. killing incoming reader daemon')
                return
            debug_print('_handle_socket_incoming yielded', msg)
            if messaging.is_message_with_header_string(msg, 'C2S_HELLO'):
                if self._i_should_refuse_clients():
                    messaging.write_msg_to(sock, messaging.M_S2S_REFUSE())
                    logging.info(("Refused a client at {addr} "
                                  "Server loads are currently approx. {loads}."
                                  ).format(addr=addr,
                                  loads=self._server_client_load))
                    return

                debug_print('new client!')
                # yields STOPITERATION on crash???
                player_id = next(self._knight_id_generator)
                logging.info(("Generated player/knight ID {player_id} "
                              "for the new client."
                              ).format(player_id=player_id))

                spawn_msg = messaging.M_SPAWN(self._server_id, player_id)
                logging.info(("Enqueued spawn request {spawn_msg} "
                              "for the new client."
                              ).format(spawn_msg=spawn_msg))
                self._requests.enqueue(spawn_msg)
                client_secret = Server._client_secret(addr[0], tuple(player_id), msg.args[0], self._dragon_arena.key)
                welcome = messaging.M_S2C_WELCOME(self._server_id, player_id, client_secret)
                logging.info(("Derived client secret {client_secret}."
                              ).format(client_secret=client_secret))
                debug_print('welcome', welcome)
                messaging.write_msg_to(sock, welcome)
                debug_print('welcomed it!')
                self._client_sockets[addr] = sock
                self._handle_client_incoming(sock, addr, player_id)
                return
            elif messaging.is_message_with_header_string(msg,'C2S_HELLO_AGAIN'):
                if self._i_should_refuse_clients():
                    messaging.write_msg_to(sock, messaging.M_S2S_REFUSE())
                    logging.info(("Refused a client at {addr} "
                                  "Server loads are currently approx. {loads}."
                                  ).format(addr=addr,
                                           loads=self._server_client_load))
                    return
                debug_print('returning client!')
                salt = msg.args[0]
                knight_id = msg.args[1]
                secret = msg.args[2]
                #ip, player_id, client_random_salt
                secret_should_be = Server._client_secret(addr[0], tuple(knight_id), salt, self._dragon_arena.key)
                if secret != secret_should_be:
                    debug_print('secret mismatch!')
                    logging.info(("Refused a client`s reconnection. Secret was {secret} but should have been {secret_should_be}."
                                  ).format(secret_should_be=secret_should_be,
                                           secret=secret))
                    messaging.write_msg_to(sock, messaging.M_S2S_REFUSE())
                else:

                    logging.info(("Client successfully reconnected with secret {secret}."
                                  ).format(secret=secret))
                    welcome = messaging.M_S2C_WELCOME(self._server_id, knight_id, secret)
                    logging.info(("Derived client secret {client_secret}."
                                  ).format(client_secret=secret))
                    debug_print('welcome', welcome)
                    messaging.write_msg_to(sock, welcome)
                    debug_print('welcomed it back!')
                    self._client_sockets[addr] = sock
                    self._handle_client_incoming(sock, addr, player_id)
                return
            elif msg.header_matches_string('S2S_HELLO'):
                debug_print('server is up! synced by someone else server!')
                self._server_sockets[msg.sender] = sock
                messaging.write_msg_to(sock, messaging.M_S2S_WELCOME(self._server_id))
                return
            elif msg.msg_header == messaging.header2int['S2S_SYNC_REQ']:
                logging.info(("This is server {s_id} that wants to sync! Killing incoming handler. wouldn't want to interfere with main thread").format(s_id=msg.sender))
                self._waiting_sync_server_tuples.enqueue((msg.sender, sock))
                debug_print('newcomer handler exiting')
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
                logging.info(("Incoming daemon noticed client at {addr} crashed."
                              "Removing client"
                              ).format(addr=addr))
                self._requests.enqueue(messaging.M_DESPAWN(self._server_id, player_id))
                self._client_sockets.pop(addr)
                #TODO debug why a client cannot REJOIN
                break
            #TODO overwrite the SENDER field. this is needed for logging AND to make sure the request is valid
            msg.sender = player_id # Server annotates this to ensure client doesnt doctor their packets
            debug_print('client incoming', msg)
            self._requests.enqueue(msg)
            logging.info(("Got client incoming {msg}!").format(msg=str(msg)))
            pass
        debug_print('client handler dead :(')

    @staticmethod
    def _client_secret(ip, player_id, client_random_salt, dragon_arena_key):
        logging.info("GEN SECRET {} {} {} {}".format(ip, player_id, client_random_salt, dragon_arena_key))
        m = hashlib.md5()
        m.update(str(ip))
        m.update(str(player_id))
        m.update(str(client_random_salt))
        m.update(str(dragon_arena_key))
        return m.hexdigest()

    def main_loop(self):
        logging.info(("Main loop started. tick_id is {tick_id}").format(tick_id=self._tick_id()))
        debug_print('MAIN LOOP :)')
        while True:
            tick_start = time.time()
            debug_print('tick', self._tick_id())

            '''SWAP BUFFERS'''
            my_req_pool = self._requests.drain_if_probably_something()
            logging.info(("drained ({num_reqs}) requests in tick {tick_id}").format(num_reqs=len(my_req_pool), tick_id=self._tick_id()))
            '''FLOOD REQS'''
            self._step_flood_reqs(my_req_pool)

            current_sync_tuples = self._waiting_sync_server_tuples.drain_if_probably_something()
            if current_sync_tuples:
                debug_print('---eyyy there are current sync tuples!---', current_sync_tuples)
                # collect DONES before sending your own
                logging.info(("servers {set} waiting to sync! LEADER tick."
                              "Suppressing DONE step"
                              ).format(set=map(lambda x: x[0], current_sync_tuples)))
                '''READ REQS AND WAIT'''
                my_req_pool.extend(self._step_read_reqs_and_wait())
                '''SORT REQ SEQUENCE'''
                req_sequence = ordering_func(my_req_pool, self._tick_id())
                '''APPLY AND LOG'''
                _apply_and_log_all(self._dragon_arena, req_sequence)
                '''### SPECIAL SYNC STEP ###''' # returns when sync is complete
                self._step_sync_servers(current_sync_tuples)
                logging.info(("Sync finished. Releasing DONE flood for tick {tick_id}"
                             ).format(tick_id=self._tick_id()))
                '''<<STEP FLOOD DONE>>'''
                self._step_flood_done(except_server_ids={serv_addr for serv_addr, sock in current_sync_tuples},
                                        tick_count_modifier=-1)

            else: #NO SERVERS WAITING TO SYNC
                # send own DONES before collecting those of others
                logging.info(("No servers waiting to sync. Normal tick").format())
                '''<<STEP FLOOD DONE>>'''
                self._step_flood_done(except_server_ids={})
                '''READ REQS AND WAIT'''
                my_req_pool.extend(self._step_read_reqs_and_wait())
                '''SORT REQ SEQUENCE'''
                req_sequence = ordering_func(my_req_pool, self._tick_id())
                '''APPLY AND LOG'''
                _apply_and_log_all(self._dragon_arena, req_sequence)

            '''UPDATE CLIENTS'''
            self._step_update_clients()

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
        for server_id, sock in enumerate(self._server_sockets):
            if sock is None:
                 self._server_client_load[server_id] = None
        my_load = len(self._client_sockets)
        self._server_client_load[self._server_id] = my_load
        total_active_loads = filter(lambda x: x is not None, self._server_client_load)
        total_num_servers = len(total_active_loads)
        if total_num_servers == 1:
            debug_print('there is no other server!')
            return False
        if my_load < max(0, das_game_settings.min_server_client_capacity):
            debug_print('I can certainly take more')
            return False
        average_server_load = rough_total_clients / float(total_num_servers)
        return my_load > (average_server_load * das_game_settings.server_overcapacity_ratio)

    def _active_server_indices(self):
        return filter(
            lambda x: self._server_sockets[x] is not None,
            range(das_game_settings.num_server_addresses),
        )

    def _step_flood_reqs(self, my_req_pool):
        for serv_id, sock in enumerate(self._server_sockets):
            if sock is None:
                #TODO put back in
                #logging.info(("Skipping req flood to server_id {serv_id} (No socket)").format(serv_id=serv_id))
                continue
            try:
                messaging.write_many_msgs_to(sock, my_req_pool)
                logging.info(("Finished flooding reqs to serv_id {serv_id}").format(serv_id=serv_id))
            except:
                 logging.info(("Flooding reqs to serv_id {serv_id} crashed!").format(serv_id=serv_id))

    def _step_flood_done(self, except_server_ids, tick_count_modifier=0):
        # need to specify except_server_ids of newly-synced server. this prevents them from getting an extra DONE
        done_msg = messaging.M_DONE(self._server_id, self._tick_id() + tick_count_modifier, len(self._client_sockets))
        logging.info(("Flooding reqs done for tick_id {tick_id} to {servers}"
                      ).format(tick_id=self._tick_id(),
                               servers=self._active_server_indices()))
        '''SEND DONE'''
        for server_id in self._active_server_indices():
            if server_id in except_server_ids:
                logging.info(("Suppressing {server_id}'s DONE message."
                              "It was newly synced and wasn't part of the barrier."
                              ).format(server_id=server_id))
                continue
            sock = self._server_sockets[server_id]
            if messaging.write_msg_to(sock, done_msg):
                logging.info(("sent {done_msg} to server_id {server_id}"
                             ).format(done_msg=done_msg, server_id=server_id))

                # crash

    def _step_read_reqs_and_wait(self):
        res = []
        active_indices = self._active_server_indices()
        logging.info("reading and waiting for servers {active_indices}".
                     format(active_indices=active_indices))
        debug_print('other servers:', self._server_sockets)

        # Need to lock down the servers I am waiting for. SYNCED servers might join inbetween
        waiting_for = list(self._active_servers())
        debug_print('waiting for ', waiting_for)
        for server_id, sock in waiting_for:
            temp_batch = []
            debug_print('expecting done from ', server_id)
            while True:
                msg = messaging.read_msg_from(sock, timeout=das_game_settings.max_done_wait)
                if messaging.is_message_with_header_string(msg, 'DONE'):
                    other_tick_id = msg.args[0]
                    self._server_client_load[server_id] = msg.args[1]
                    debug_print('got a DONE')
                    if other_tick_id != self._tick_id():
                        debug_print(("___\nme   ({})\t{}\nthem ({})\t{}\n***"
                              ).format(self._server_id, self._tick_id(), server_id, other_tick_id))
                    # DONE got. accept the batch
                    res.extend(temp_batch)
                    break
                elif isinstance(msg, Message):
                    # some other request message BEFORE a done
                    temp_batch.append(msg)
                else:
                    if msg is MessageError.CRASH:
                        logging.info(("Wait&recv for {server_id} ended in CRASH"
                                     ).format(server_id=server_id))
                    else:
                        logging.info(("Wait&recv for {server_id} ended in TIMEOUT"
                                      "(might be a deadlock?)"
                                     ).format(server_id=server_id))
                    debug_print('Lost connection!')
                    # Clean up, discard temp_batch
                    self._server_sockets[server_id] = None
                    break

        debug_print('server load', self._server_client_load[self._server_id])
        logging.info("Released from the barrier")
        debug_print("!!!RELEASED FROM TICK", self._tick_id())
        logging.info(("Starting tick {tick_id}").format(tick_id=self._tick_id()))
        return res


    def _tick_id(self):
        return self._dragon_arena.get_tick()

    def _step_sync_servers(self, sync_tuples):
        #synced server has the NEXT tick_d as the starting tick, as they start with the 'freshly synced' state
        #TODO ensure tick IDs are matching up
        update_msg = messaging.M_S2S_SYNC_REPLY(self._tick_id(),
                                                self._dragon_arena.serialize())

        # TODO clean up. check correctness
        for sender_id, socket in sync_tuples:
            if socket is None:
                continue
            debug_print('sync tup:', sender_id, socket)
            if messaging.write_msg_to(socket, update_msg):
                logging.info(("Sent sync msg {update_msg} to waiting server "
                              "{sender_id}").format(update_msg=update_msg,
                                                    sender_id=sender_id))
            else:
                debug_print('failed to send sync msg')
                break
                logging.info(("Failed to send sync msg to waiting server "
                              "{sender_id}").format(sender_id=sender_id))

            debug_print('awaiting SYNC DONE from ',sender_id,'...')
            logging.info(("awaiting SYNC DONE from {sender_id}...  "
                          ).format(sender_id=sender_id))
            sync_done = messaging.read_msg_from(socket, timeout=das_game_settings.max_server_sync_wait)
            if messaging.is_message_with_header_string(sync_done, 'S2S_SYNC_DONE'):
                logging.info(("Got {msg} from sync server {sender_id}! "
                              ":)").format(msg=sync_done, sender_id=sender_id))
                debug_print('SYNCED',sender_id,'YA, BUDDY :)')
                self._server_sockets[sender_id] = socket
                logging.info(("Spawned incoming handler for"
                              "newly-synced server {sender_id}"
                             ).format(sender_id=sender_id))
            else:
                debug_print('either timed out or crashed. either way, disregarding')
                logging.info(("Hmm. It seems that {sender_id} has"
                              "crashed before syncing. Oh well :/"
                             ).format(sender_id=sender_id))

        logging.info(("Got to end of sync").format())

    def _step_update_clients(self):
        update_msg = messaging.M_UPDATE(self._server_id, self._tick_id(), self._dragon_arena.serialize())
        logging.info(("Update msg ready for tick {tick_id}"
                     ).format(tick_id=self._tick_id()))
        logging.info(("Client set for tick {tick_id}: {clients}"
                     ).format(tick_id=self._tick_id(), clients=self._client_sockets.keys()))
        debug_print('CLIENT SOCKS', self._client_sockets)
        for addr, sock in self._client_sockets.iteritems():
            #TODO investigate why addr is an ip and not (ip,port)
            if messaging.write_msg_to(sock, update_msg):
                debug_print('updated client', addr)
                logging.info(("Successfully updated client at addr {addr}"
                              "for tick_id {tick_id}"
                              ).format(addr=addr,
                                       tick_id=self._tick_id()))
            else:
                logging.info(("Failed to update client at addr {addr}"
                              "for tick_id {tick_id}"
                              ).format(addr=addr,
                                       tick_id=self._tick_id()))
                self._client_sockets.pop(addr)
        logging.info(("All updates done for tick_id {tick_id}"
                     ).format(tick_id=self._tick_id()))
