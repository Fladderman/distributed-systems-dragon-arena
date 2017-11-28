import threading, time, json, socket, sys, os, logging
import messaging, das_game_settings, protected
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
from DragonArenaNew import Creature, Knight, Dragon, DragonArena

def ordering_func(reqs):
    logging.info(("Applying ORDERING function to ({num_reqs}) reqs.").format(num_reqs=len(reqs)))
    req_sequence = []
    #TODO
    return req_sequence

class ServerAcceptor:
    def __init__(self, port):
        assert type(port) is int and port > 0
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", port))
        self._sock.listen(das_game_settings.backlog)

    def next_incoming(self):
        try:
            client_socket, addr = self._sock.accept()
            return client_socket, addr
        except:
            return None, None

class Server:
    def __init__(self, server_id):
        log_filename = ('server_{s_id}.log').format(s_id=server_id)
        logging.basicConfig(filename=log_filename, filemode='w', level=logging.INFO)
        logging.info(("{line}\nServer {server_id} started logging at {time}\n{line}").format(line='==========\n', server_id=server_id, time=time.time()))
        self._server_id = server_id
        backoff_time = 0.1
        try_index = 0
        while True:
            time.sleep(backoff_time)
            logging.info(("try number {try_index}").format(try_index=try_index))
            try_index += 1
            # TODO backoff time, try again when this throws exception
            self.try_setup()
            self.main_loop()
            return


    def try_setup(self):
        auth_sock, auth_index = self._connect_to_first_other_server()
        logging.info(("authority socket_index: {index}").format(index=auth_index))
        if auth_sock == None:
            # I am first! :D
            logging.info(("I am the first server!").format())
            self._dragon_arena = Server.create_fresh_arena()
            self._tick_id = 0
            self._server_sockets = [None for _ in xrange(0, das_game_settings.num_server_addresses)]
        else:
            # I'm not first :[
            sync_req = messaging.M_S2S_SYNC_REQ(self._server_id)
            logging.info(("I am NOT the first server!. Will sync with auth_index. sending msg {sync_req}").format(sync_req=sync_req))
            messaging.write_msg_to(auth_sock, sync_req)
            sync_reply = messaging.read_msg_from(auth_sock)
            logging.info(("Got sync reply: {reply}").format(reply=str(sync_reply)))
            assert sync_reply.msg_header == messaging.header2int['S2S_SYNC_REPLY']
            self._tick_id = DragonArena.deserialize(sync_reply.args[0])
            logging.info(("Got sync'd game state from server! serialized: {serialized_state}").format(serialized_state=sync_reply.args[1]))
            self._dragon_arena = DragonArena.deserialize(sync_reply.args[1])
            self._server_sockets = Server._socket_to_others({auth_index, server_id})
            hello_msg = messaging.M_S2S_HELLO(server_id)
            for i, s in enumerate(self._server_sockets):
                try:
                    messaging.write_msg_to(auth_sock, hello_msg)
                    reply2 = messaging.read_msg_from(auth_sock,timeout=False)
                    logging.info(("Successfully HELLO'd server {i} with {hello_msg}").format(i=i, hello_msg=hello_msg))
                    if reply2.msg_header == messaging.header2int['S2S_WELCOME']:
                        logging.info(("got expected WELCOME reply from {i}").format(i=i))
                    else:
                        logging.info(("instead of WELCOME from {i}, got {msg}").format(i=i, msg=reply2))
                except:
                    logging.info(("Couldn't HELLO server {i} with {hello_msg}. Oh well.").format(i=i, hello_msg=hello_msg))
            messaging.write_msg_to(auth_sock, messaging.M_S2S_SYNC_DONE)

        self._requests = protected.ProtectedQueue()
        self._waiting_sync_server_tuples = protected.ProtectedQueue() #(msg.sender, socket)
        self._client_sockets = dict()
        self._kick_off_acceptor()
        # all went ok :)

    def _connect_to_first_other_server(self):
        for index, addr in enumerate(das_game_settings.server_addresses):
            if index == self._server_id: continue # skip myself
            sock = Server._try_connect_to(addr)
            if sock != None:
                return sock, index
        return None, None

    @staticmethod
    def _socket_to_others(except_indices):
        f = lambda i: None if i in except_indices else _try_connect_to(das_game_settings.server_addresses[i])
        return list(map(f, xrange(0, das_game_settings.num_servers)))


    @staticmethod
    def _try_connect_to(addr): #addr == (ip, port)
        socket.setdefaulttimeout(0.3) #todo experiment with this
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        logging.info(("Created fresh arena {d}").format(d=d.serialize()))
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
        while True:
            # print('acc loop')
            new_socket, new_addr = server_acceptor.next_incoming()
            if new_socket != None:
                logging.info(("new acceptor connection from {addr}").format(addr=new_addr))
                # print('new_client_tuple', (new_addr, new_socket))
                #TODO handle the case that this new_addr is already associated with something
                self._client_sockets[new_addr] = new_socket
                client_incoming_thread = threading.Thread(
                    target=Server._handle_socket_incoming,
                    args=(self, new_socket, new_addr),
                )
                client_incoming_thread.daemon = True
                client_incoming_thread.start()

    def _handle_socket_incoming(self, socket, addr):
        logging.info(("handling messages from newcomer socket at {addr}").format(addr=addr))
        for msg in messaging.generate_messages_from(socket,timeout=False):
            logging.info(("newcomer socket sent {msg}").format(msg=str(msg)))
            if msg == None:
                print('sock dead. killing incoming reader daemon')
                return
            print('msg yielded', msg)
            if msg.msg_header == messaging.header2int['C2S_HELLO']: #todo check server secret
                messaging.write_msg_to(socket, messaging.M_S2C_WELCOME(self._server_id))
                if True: # TODO if not above client capacity
                    self._handle_client_incoming(socket, addr)
            elif msg.msg_header == messaging.header2int['S2S_HELLO']:
                messaging.write_msg_to(socket, messaging.M_S2S_WELCOME(self._server_id))
                self._handle_server_incoming(socket, addr)
            elif msg.msg_header == messaging.header2int['S2S_SYNC_REQ']:
                logging.info(("This is server {s_id} that wants to sync! Killinig incoming handler. wouldn't want to interfere with main thread").format(s_id=msg.sender))
                self._waiting_sync_server_tuples.enqueue((msg.sender, socket))


    def _handle_client_incoming(self, socket, addr):
        for msg in messaging.generate_messages_from(socket, timeout=False):
            logging.info(("Got client incoming {msg}!").format(msg=str(msg)))
            pass

    def _handle_server_incoming(self, socket, addr):
        for msg in messaging.generate_messages_from(socket, timeout=False):
            logging.info(("Got server incoming {msg}!").format(msg=str(msg)))
            pass

    @staticmethod
    def _generate_msgs_until_done_or_crash(sock):
        for msg in messaging.generate_messages_from(sock, timeout=True):
            if msg != None:
                if msg.header_matches_string('DONE'): return
                else: yield msg

    @staticmethod
    def _apply_and_log(dragon_arena, message, log_filename):
        assert isinstance(dragon_arena, DragonArena)
        assert isinstance(message, messaging.Message)
        logging.info(("SORTED REQ: {req}").format(req=str(message)))
        #TODO branch. decide what to do. writ result to log
        pass


    def main_loop(self):
        logging.info(("Main loop started. tick_id is {tick_id}").format(tick_id=self._tick_id))
        print('MAIN LOOP :)')
        while True:
            tick_start = time.time()
            print('tick')

            '''SWAP BUFFERS'''
            my_req_pool = self._requests.drain_if_probably_something()
            logging.info(("drained ({num_reqs}) requests in tick {tick_id}").format(num_reqs=len(my_req_pool), tick_id=self._tick_id))


            '''FLOOD REQS'''
            self._step_flood_reqs(my_req_pool)

            current_sync_tuples = self._waiting_sync_server_tuples.drain_if_probably_something()
            if current_sync_tuples:
                logging.info(("servers {set} waiting to sync! LEADER tick. Suppressing DONE step").format(set=map(lambda x: x[0], current_sync_tuples)))
                '''READ REQS AND WAIT'''
                my_req_pool.extend(self._step_read_reqs_and_wait())
                logging.info(("Got all DONES. LEADER proceeding past barrier solo! boy I hope I don't deadlock ;)").format())
                '''SORT REQ SEQUENCE'''
                req_sequence = ordering_func(my_req_pool)
                '''APPLY AND LOG'''
                for req in req_sequence:
                    Server._apply_and_log(self._dragon_arena, req)
                '''### SPECIAL SYNC STEP ###''' # returns when sync is complete
                # TODO no need to serialize the state a 2nd time. calc once and pass into both funcs
                self._step_sync_servers(current_sync_tuples)
                logging.info(("Sync finished. Releasing DONE flood for tick {tick_id}").format(tick_id=self._tick_id))
                '''STEP FLOOD DONE'''
                self._step_flood_done()


            else: #NO SERVERS WAITING TO SYNC
                logging.info(("No servers waiting to sync. Normal tick").format())
                '''STEP FLOOD DONE'''
                self._step_flood_done()
                '''READ REQS AND WAIT'''
                my_req_pool.extend(self._step_read_reqs_and_wait())
                '''SORT REQ SEQUENCE'''
                req_sequence = ordering_func(my_req_pool)
                '''APPLY AND LOG'''
                for req in req_sequence:
                    Server._apply_and_log(self._dragon_arena, req)


            '''UPDATE CLIENTS'''
            self._step_update_clients()

            '''SLEEP STEP'''
            sleep_time = das_game_settings.server_min_tick_time - (time.time() - tick_start)
            if sleep_time > 0.0:
                logging.info(("Sleeping for ({sleep_time}) seconds for ick_id {tick_id}").format(sleep_time=sleep_time, tick_id=self._tick_id))
                time.sleep(sleep_time)
            else:
                logging.info(("No time for sleep for tick_id {tick_id}").format(tick_id=self._tick_id))

            logging.info(("Tick {tick_id} complete").format(tick_id=self._tick_id))
            self._tick_id += 1

    def _step_flood_reqs(self, my_req_pool):
        for serv_id, sock in enumerate(self._server_sockets):
            if sock == None:
                #TODO put back in
                #logging.info(("Skipping req flood to server_id {serv_id} (No socket)").format(serv_id=serv_id))
                continue
            try:
                messaging.write_many_msgs_to(sock, my_req_pool)
                logging.info(("Finished flooding reqs to serv_id {serv_id}").format(serv_id=serv_id))
            except:
                 logging.info(("Flooding reqs to serv_id {serv_id} crashed!").format(serv_id=serv_id))

    def _step_flood_done(self):
        done_msg = messaging.M_DONE
        logging.info(("Flooding reqs done for tick_id {tick_id}").format(tick_id=self._tick_id))
        '''SEND DONE'''
        for sock in self._server_sockets:
            try: messaging.write_msg_to(sock, done_msg)
            except: pass # reader will remove it

    def _step_read_reqs_and_wait(self):
        res = []
        for serv_id, sock in enumerate(self._server_sockets):
            if sock==None:
                #TODO put back in
                #logging.info(("Not waiting for DONE from {serv_id} (No socket)").format(serv_id=serv_id))
                pass
            else:
                msgs = list(Server._generate_msgs_until_done_or_crash(sock))
                res.extend(msgs)
                logging.info(("Got DONE from {serv_id} after ({num_reqs}) reqs. Total reqs == {total}").format(serv_id=serv_id, num_reqs=len(msgs), total=len(my_req_pool)))
        return res

    def _step_sync_servers(self, sync_tuples):
        update_msg = messaging.M_S2S_SYNC_REPLY(self._tick_id, self._dragon_arena.serialize())
        for sender_id, socket in sync_tuples:
            try:
                messaging.write_msg_to(socket, update_msg)
                logging.info(("Sent sync msg to waiting server {sender_id}").format(sender_id=sender_id))
            except:
                logging.info(("Failed to send sync msg to waiting server {sender_id}").format(sender_id=sender_id))

        for sender_id, socket in sync_tuples:
            try:
                reply = messaging.read_msg_from(socket, timeout=False)
                if reply != None and reply.header_matches_string('S2S_SYNC_DONE'):
                     logging.info(("Got {msg} from sync server {sender_id}! :)").format(msg=reply, sender_id=sender_id))
                     self._server_sockets[sender_id] = socket
                     server_incoming_thread = threading.Thread(
                         target=Server._handle_server_incoming,
                         args=(self, socket, das_game_settings.server_addresses[sender_id]),
                     )
                     logging.info(("Spawned incoming handler for newly-synced server {sender_id}").format(sender_id=sender_id))
            except:
                logging.info(("Hmm. It seems that {sender_id} has crashed before syncing. Oh well :/").format(sender_id=sender_id))

    def _step_update_clients(self):
        update_msg = messaging.M_UPDATE(self._server_id, self._tick_id, self._dragon_arena.serialize())
        logging.info(("Update msg ready for tick {tick_id}").format(tick_id=self._tick_id))
        for addr, sock in self._client_sockets:
            #TODO investigate why addr is an ip and not (ip,port)
            try:
                messaging.write_msg_to(sock, update_msg)
                logging.info(("Successfully updated client at addr {addr} for tick_id {tick_id}").format(addr=addr, tick_id=self._tick_id))
            except:
                logging.info(("Failed to update client at addr {addr} for tick_id {tick_id}").format(addr=addr, tick_id=self._tick_id))
        logging.info(("All updates done for tick_id {tick_id}").format(tick_id=self._tick_id))
