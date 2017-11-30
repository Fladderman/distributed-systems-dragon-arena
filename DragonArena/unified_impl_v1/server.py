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
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
from DragonArenaNew import Creature, Knight, Dragon, DragonArena

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
    for msg in message_sequence:
        assert isinstance(msg, messaging.Message)

        if msg.sender != msg.args[0]:
            # git negged, do log
            continue

        # valid = msg.permitted_in_server_application_function() and ``correct sender``


        if msg.header_matches_string("R_MOVE"):
            print "666"
        elif msg.header_matches_string("R_HEAL"):
            print "999"
        elif msg.header_matches_string("R_ATTACK"):
            print "boo"

        # TODO ensure this message is sent from a SERVER (id will be Int). not a CLIENT (id is a tuple
        # tuple(msg.arg[0]) is the id of the newly-spawned knight.
        # be sure to create it on the board somewhere deterministically
        elif msg.header_matches_string("SPAWN"):
            print "zoopy"
        else:
            raise "chris fukt up damn"
        # TODO mutate the dragon_arena in response to each message in sequence.
        # TODO log each outcome with a clear error msg
        logging.info("Application of {msg} resulted in ...".format(
            msg=str(msg)))
    pass

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
            # except:
            #     print('ACCEPTOR HAD A PROBLEM!')
        except GeneratorExit:
            print('acceptor generator killed')
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
                print('try setup exception. backing off', e)
                time.sleep(backoff_time)
                backoff_time *= 2
                continue
            self._kick_off_acceptor()
            self.main_loop()
            return

    def try_setup(self):
        '''Will throw exceptions upwards if things fail'''
        print('OK')
        auth_sock, auth_index = self._connect_to_first_other_server()
        print(auth_sock, auth_index)
        logging.info("authority socket_index: {index}".format(
            index=auth_index))
        if auth_sock is None:
            # I am first! :D
            print('I AM THE FIRST SERVER:', auth_index)
            logging.info("I am the first server!".format())
            self._dragon_arena = Server.create_fresh_arena()
            self._tick_id = 0
            self._server_sockets = \
                [None for _ in xrange(0, das_game_settings.
                                      num_server_addresses)]
        else:
            # I'm not first :[
            print('AUTHORITY SERVER:', auth_index)
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
            self._tick_id = sync_reply.args[0]
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

        print('WOOOHOOO READY')
        self._requests = protected.ProtectedQueue()
        self._waiting_sync_server_tuples = protected.ProtectedQueue() #(msg.sender, socket)
        self._client_sockets = dict()
        self._knight_id_generator = self._knight_id_generator_func()


    def _knight_id_generator_func(self):
        largest_taken_id_for_me =\
            max(# largest index of my knights
                map(# counter of my knights
                    lambda x: x[1],
                    filter(# MY KNIGHTS
                        lambda x: x[0]==self._server_id,
                        list(
                            self._dragon_arena.get_knights(), # ALL KNIGHTS
                        ) + [(self._server_id, -1)] #default
                    ),
                )
            )

        logging.info(("Prepared knight ID generator."
                      "Will count up from ({server_id},{next_knight_id})"
                      ).format(server_id=self._server_id,
                               next_knight_id=largest_taken_id_for_me+1))
        try:
            for i in count_up_from(largest_taken_id_for_me + 1):
                yield (self._server_id, i)
        finally:
            print('Cleaning up _knight_id_generator')
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
        logging.info(("Created fresh arena  with settings {settings}"
                     ).format(settings=das_game_settings.dragon_arena_init_settings))
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
            print('acceptor got', new_socket, new_addr)
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
                print('newcomer socket died in the cradle :(. Hopefully just a ping. killing incoming reader daemon')
                return
            print('_handle_socket_incoming yielded', msg)
            if messaging.is_message_with_header_string(msg, 'C2S_HELLO'):
                print('new client!')
                player_id = next(self._knight_id_generator)
                logging.info(("Generated player/knight ID {player_id} "
                              "for the new client."
                              ).format(player_id=player_id))

                spawn_msg = messaging.M_SPAWN(player_id)
                logging.info(("Enqueued spawn request {spawn_msg} "
                              "for the new client."
                              ).format(spawn_msg=spawn_msg))
                self._requests.enqueue(spawn_msg)
                welcome = messaging.M_S2C_WELCOME(self._server_id, player_id)
                print('welcome', welcome)
                messaging.write_msg_to(sock, welcome)
                print('welcomed it!')
                if True: # TODO if not above client capacity
                    self._client_sockets[addr] = sock
                    self._handle_client_incoming(sock, addr, player_id)
                return
            elif msg.header_matches_string('S2S_HELLO'):
                print('server is up! synced by someone else server!')
                self._server_sockets[msg.sender] = sock
                messaging.write_msg_to(sock, messaging.M_S2S_WELCOME(self._server_id))
                # self._handle_server_incoming(socket, addr)
                return
            elif msg.msg_header == messaging.header2int['S2S_SYNC_REQ']:
                logging.info(("This is server {s_id} that wants to sync! Killing incoming handler. wouldn't want to interfere with main thread").format(s_id=msg.sender))
                self._waiting_sync_server_tuples.enqueue((msg.sender, sock))
                # print('OK KILLING GENERATOR?')
                print('newcomer handler exiting')
                # time.sleep(1000)
                # generator.close()
                return

    def _handle_client_incoming(self, sock, addr, player_id):
        #TODO this function gets as param the player's knight ID
        #TODO before submitting it as a request, this handler wi
        print('client handler!')
        # for msg in messaging.generate_messages_from(socket, timeout=None):
        while True:
            msg = messaging.read_msg_from(sock, timeout=None)
            print('client sumthn')
            if msg == MessageError.CRASH:
                print('client crashed!')
                logging.info(("Incoming daemon noticed client at {addr} crashed."
                              "Removing client"
                              ).format(addr=addr))
                self._client_sockets.pop(addr)
                #TODO debug why a client cannot REJOIN
                break
            #TODO overwrite the SENDER field. this is needed for logging AND to make sure the request is valid
            msg.sender = player_id # Server annotates this to ensure client doesnt doctor their packets
            print('client incoming', msg)
            self._requests.enqueue(msg)
            logging.info(("Got client incoming {msg}!").format(msg=str(msg)))
            pass
        print('client handler dead :(')

    def main_loop(self):
        logging.info(("Main loop started. tick_id is {tick_id}").format(tick_id=self._tick_id))
        print('MAIN LOOP :)')
        while True:
            tick_start = time.time()
            print('tick', self._tick_id)

            '''SWAP BUFFERS'''
            my_req_pool = self._requests.drain_if_probably_something()
            logging.info(("drained ({num_reqs}) requests in tick {tick_id}").format(num_reqs=len(my_req_pool), tick_id=self._tick_id))
            '''FLOOD REQS'''
            self._step_flood_reqs(my_req_pool)

            current_sync_tuples = self._waiting_sync_server_tuples.drain_if_probably_something()
            if current_sync_tuples:
                print('---eyyy there are current sync tuples!---', current_sync_tuples)
                # collect DONES before sending your own
                logging.info(("servers {set} waiting to sync! LEADER tick."
                              "Suppressing DONE step"
                              ).format(set=map(lambda x: x[0], current_sync_tuples)))
                '''READ REQS AND WAIT'''
                my_req_pool.extend(self._step_read_reqs_and_wait())
                '''SORT REQ SEQUENCE'''
                req_sequence = ordering_func(my_req_pool, self._tick_id)
                '''APPLY AND LOG'''
                _apply_and_log_all(self._dragon_arena, req_sequence)
                '''### SPECIAL SYNC STEP ###''' # returns when sync is complete
                self._step_sync_servers(current_sync_tuples)
                logging.info(("Sync finished. Releasing DONE flood for tick {tick_id}"
                             ).format(tick_id=self._tick_id))
                '''<<STEP FLOOD DONE>>'''
                self._step_flood_done(except_server_ids={serv_addr for serv_addr, sock in current_sync_tuples})

            else: #NO SERVERS WAITING TO SYNC
                # send own DONES before collecting those of others
                logging.info(("No servers waiting to sync. Normal tick").format())
                '''<<STEP FLOOD DONE>>'''
                self._step_flood_done(except_server_ids={})
                '''READ REQS AND WAIT'''
                my_req_pool.extend(self._step_read_reqs_and_wait())
                '''SORT REQ SEQUENCE'''
                req_sequence = ordering_func(my_req_pool, self._tick_id)
                '''APPLY AND LOG'''
                _apply_and_log_all(self._dragon_arena, req_sequence)

            '''UPDATE CLIENTS'''
            self._step_update_clients()

            '''SLEEP STEP'''
            # TODO put back in later
            # if self._waiting_sync_server_tuples.poll_nonempty():
            #     logging.info(("Some servers want to sync! no time to sleep on tick {tick_id}"
            #                  ).format(tick_id=self._tick_id))
            # else:

            sleep_time = das_game_settings.server_min_tick_time - (time.time() - tick_start)
            if sleep_time > 0.0:
                logging.info(("Sleeping for ({sleep_time}) seconds for tick_id {tick_id}"
                             ).format(sleep_time=sleep_time, tick_id=self._tick_id))
                time.sleep(sleep_time)
            else:
                logging.info(("No time for sleep for tick_id {tick_id}"
                             ).format(tick_id=self._tick_id))



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

    def _step_flood_done(self, except_server_ids):
        # need to specify except_server_ids of newly-synced server. this prevents them from getting an extra DONE
        done_msg = messaging.M_DONE(self._server_id, self._tick_id)
        logging.info(("Flooding reqs done for tick_id {tick_id} to {servers}"
                      ).format(tick_id=self._tick_id,
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
        print('other servers:', self._server_sockets)

        # Need to lock down the servers I am waiting for. SYNCED servers might join inbetween
        waiting_for = list(self._active_servers())
        print('waiting for ', waiting_for)
        for server_id, sock in waiting_for:
            temp_batch = []
            print('expecting done from ', server_id)
            while True:
                msg = messaging.read_msg_from(sock, timeout=das_game_settings.max_done_wait)
                if messaging.is_message_with_header_string(msg, 'DONE'):
                    other_tick_id = msg.args[0]
                    print('got a DONE')
                    if other_tick_id != self._tick_id:
                        print(("___\nme   ({})\t{}\nthem ({})\t{}\n***"
                              ).format(self._server_id, self._tick_id, server_id, other_tick_id))
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
                    print('Lost connection!')
                    # Clean up, discard temp_batch
                    self._server_sockets[server_id] = None
                    break


        logging.info("Released from the barrier")
        print("!!!RELEASED FROM TICK", self._tick_id)
        self._tick_id += 1
        logging.info(("Starting tick {tick_id}").format(tick_id=self._tick_id))
        # time.sleep(0.3)
        return res

    def _step_sync_servers(self, sync_tuples):
        #synced server has the NEXT tick_d as the starting tick, as they start with the 'freshly synced' state
        #TODO ensure tick IDs are matching up
        update_msg = messaging.M_S2S_SYNC_REPLY(self._tick_id,
                                                self._dragon_arena.serialize())

        # TODO clean up. check correctness
        for sender_id, socket in sync_tuples:
            if socket is None:
                continue
            print('sync tup:', sender_id, socket)
            if messaging.write_msg_to(socket, update_msg):
                logging.info(("Sent sync msg {update_msg} to waiting server "
                              "{sender_id}").format(update_msg=update_msg,
                                                    sender_id=sender_id))
            else:
                print('failed to send sync msg')
                break
                logging.info(("Failed to send sync msg to waiting server "
                              "{sender_id}").format(sender_id=sender_id))

            print('awaiting SYNC DONE from ',sender_id,'...')
            logging.info(("awaiting SYNC DONE from {sender_id}...  "
                          ).format(sender_id=sender_id))
            sync_done = messaging.read_msg_from(socket, timeout=das_game_settings.max_server_sync_wait)
            if messaging.is_message_with_header_string(sync_done, 'S2S_SYNC_DONE'):
                logging.info(("Got {msg} from sync server {sender_id}! "
                              ":)").format(msg=sync_done, sender_id=sender_id))
                print('SYNCED',sender_id,'YA, BUDDY :)')
                self._server_sockets[sender_id] = socket
                logging.info(("Spawned incoming handler for"
                              "newly-synced server {sender_id}"
                             ).format(sender_id=sender_id))
            else:
                print('either timed out or crashed. either way, disregarding')
                logging.info(("Hmm. It seems that {sender_id} has"
                              "crashed before syncing. Oh well :/"
                             ).format(sender_id=sender_id))

        logging.info(("Got to end of sync").format())

    def _step_update_clients(self):
        # update_msg = messaging.M_UPDATE(self._server_id, self._tick_id, 5) #TODO THIS IS DEBUG. last arg should be a serialized game state
        update_msg = messaging.M_UPDATE(self._server_id, self._tick_id, self._dragon_arena.serialize())
        logging.info(("Update msg ready for tick {tick_id}"
                     ).format(tick_id=self._tick_id))
        logging.info(("Client set for tick {tick_id}: {clients}"
                     ).format(tick_id=self._tick_id, clients=self._client_sockets.keys()))
        print('CLIENT SOCKS', self._client_sockets)
        for addr, sock in self._client_sockets.iteritems():
            #TODO investigate why addr is an ip and not (ip,port)
            if messaging.write_msg_to(sock, update_msg):
                print('updated client', addr)
                logging.info(("Successfully updated client at addr {addr}"
                              "for tick_id {tick_id}"
                              ).format(addr=addr,
                                       tick_id=self._tick_id))
            else:
                logging.info(("Failed to update client at addr {addr}"
                              "for tick_id {tick_id}"
                              ).format(addr=addr,
                                       tick_id=self._tick_id))
                self._client_sockets.pop(addr)
        logging.info(("All updates done for tick_id {tick_id}"
                     ).format(tick_id=self._tick_id))
