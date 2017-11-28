import threading, time, json, socket, sys, os, logging
import messaging, das_game_settings, protected
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
from DragonArenaNew import Creature, Knight, Dragon, DragonArena

def ordering_func(reqs):
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
        logging.basicConfig(filename=('server_{s_id}.log'),format(s_id=server_id), filemode='w', level=logging.INFO)
        logging.info("Logging started at %s", str(time.time()))
        self._server_id = server_id
        backoff_time = 0.1
        while True:
            time.sleep(backoff_time)
            try:
                self.try_setup()
                break
            except:
                backoff_time *= 2.00
        self.main_loop()

    def try_setup(self):
        auth_sock, auth_index = self.connect_to_first_other_server()
        if auth_sock == None:
            # I am first! :D
            self._dragon_arena = Server.create_fresh_arena()
            self._tick_id = 0
        else:
            # I'm not first :[
            messaging.write_msg_to(auth_sock, messaging.M_S2S_SYNC_REQ(server_id))
            sync_reply = messaging.read_msg_from(auth_sock)
            assert sync_reply.msg_header == messaging.header2int['S2S_SYNC_REPLY']
            self._tick_id = DragonArena.deserialize(sync_reply.args[0])
            self._dragon_arena = DragonArena.deserialize(sync_reply.args[1])
            self._server_socks = Server._socket_to_others({auth_index, server_id})
            for s in self._server_socks:
                try:
                    messaging.write_msg_to(auth_sock, messaging.M_S2S_HELLO(server_id))
                    reply2 = messaging.read_msg_from(auth_sock)
                assert reply2.msg_header == messaging.header2int['S2S_WELCOME']
            messaging.write_msg_to(auth_sock, messaging.M_S2S_SYNC_DONE)

        self._kick_off_acceptor()
        # all went ok :)

    @staticmethod
    def _socket_to_others(except_indices):
        f = lambda i: None if i in except_indices else _try_connect_to(das_game_settings.server_addresses[i])
        return list(map(f, xrange(0, das_game_settings.num_servers))


    @staticmethod
    def _try_connect_to(addr): #addr == (ip, port)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(addr)
            return sock
        except: return None

    def _connect_to_first_other_server(self):
        for index, addr in enumerate(das_game_settings.server_addresses):
            if index == self._server_id: continue # skip myself
            sock = Server._try_connect_to(addr)
            if sock != None:
                return sock, addr
        return None, None

    def _kick_off_acceptor(self):
        acceptor_handle = threading.Thread(
            target=Server._handle_new_connections,
            args=(self, my_port),
        )
        acceptor_handle.daemon = True
        acceptor_handle.start()

    def _sync_with_server(self, authority_server_socket):
        messaging.write_msg_to(authority_server_socket, messaging.M_SERV_SYNC_REQ)
        msg_check = lambda m:\
            isinstance(m, Message)\
            and m.msg_header == messaging.header2int['SERV_SYNC_REPLY']
        reply = messaging.read_first_message_matching(authority_server_socket, msg_check)
        return reply.args[0], reply.args[1]

    @staticmethod
    def create_fresh_arena():
        # ** unpacks dictionary as keyed arguments
        d = DragonArena(**das_game_settings.dragon_arena_init_settings)
        d.new_game()
        return d

    def _connect_to_other_servers(self):
        '''
        first try to connect to all, populating self._other_server_socks
        then send each a M_SERV_HELLO
        '''
        serv_sockets = [None for _ in range(0, das_game_settings.num_servers)]
        socket.setdefaulttimeout(3.0)
        msg = messaging.M_S2S_HELLO(self._server_id)
        for index, addr in enumerate(das_game_settings.server_addresses):
            if index == self._server_id:
                continue # skip myself
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((ip, port))
                print('successfully conencted to', index, 'at', addr)
                messaging.write_msg_to(sock, msg)
                reply = messaging.read_msg_from(sock)
                print('got reply', reply, 'from', addr)
                assert reply.msg_header == messaging.header2int['M_S2S_WELCOME']
                serv_sockets[index] = sock
            except:
                print('failed to connect to ', index, 'at', addr)
        return serv_sockets

    def _handle_socket_incoming(self, socket, addr):
        for msg in messaging.generate_messages_from(client_sock):
            if msg == None:
                continue
            print('msg yielded', msg)
            if msg.msg_header == messaging.header2int['C2S_HELLO']: #todo check server secret
                messaging.write_msg_to(socket, messaging.M_S2C_WELCOME(self._server_id))
                if True: # TODO if not above client capacity
                    self._handle_client_incoming(socket, addr)
                return
            if msg.msg_header == messaging.header2int['S2S_HELLO']:
                messaging.write_msg_to(socket, messaging.M_S2S_WELCOME(self._server_id))
                self._handle_client_incoming(socket, addr)
                return
            elif client_addr not in self._clients:
                print('sock dead. killing incoming reader daemon')
                return

    def _handle_client_incoming(self, socket, addr):
        for msg in messaging.generate_messages_from(client_sock):
            pass

    def _handle_server_incoming(self, socket, addr):
        for msg in messaging.generate_messages_from(client_sock):
            pass

    def _handle_new_connections(self, port):
        server_acceptor = ServerAcceptor(port)
        while True:
            # print('acc loop')
            if self._accepting_clients:
                new_socket, new_addr = server_acceptor.next_incoming()
                # print('new_client_tuple', (new_addr, new_socket))
                if new_socket != None and new_addr not in self._clients:
                    self._clients[new_addr] = new_socket
                    client_incoming_thread = threading.Thread(
                        target=Server._handle_socket_incoming,
                        args=(self, new_socket, new_addr),
                    )
                    client_incoming_thread.daemon = True
                    client_incoming_thread.start()
            else:
                time.sleep(1.0)

    @staticmethod
    def _generate_msgs_until_done_or_crash(sock):
        for msg in messaging.generate_messages_from(sock):
            if msg != None:
                elif msg.header_matches_string('DONE'): return
                else: yield msg

    @staticmethod
    def _apply_and_log(dragon_arena, message, log_filename):
        assert isinstance(dragon_arena, DragonArena)
        assert isinstance(message, messaging.Message)
        logging.info("Logging req %s", 'potatyr')
        #TODO
        pass

    def main_loop(self):
        while True:
            tick_start = time.time()
            print('tick')

            '''SWAP BUFFERS'''
            my_req_pool = self._requests.drain_if_probably_something()

            '''FLOOD REQS'''
            for req in my_req_pool:
                for sock in self._serv_sockets:
                    try: messaging.write_msg_to(sock, req)
                    except: pass # reader will remove it

            '''SEND DONE'''
            for sock in self._serv_sockets:
                try: messaging.write_msg_to(sock, req)
                except: pass # reader will remove it

            '''READ REQS AND WAIT'''
            for sock in self._serv_sockets:
                my_req_pool.extend(Server._generate_msgs_until_done_or_crash(sock))

            '''SORT REQ SEQUENCE'''
            req_sequence = ordering_func(my_req_pool)

            '''APPLY AND LOG'''
            for req in req_sequence:
                Server._apply_and_log(self._dragon_arena, req)

            '''UPDATE CLIENTS'''
            update_msg = messaging.M_UPDATE(self._server_id, tick_id, self._dragon_arena.serialize())
            for addr, sock in self._clients:
                messaging.write_msg_to(sock, update_msg)

            '''SLEEP STEP'''
            sleep_time = das_game_settings.server_min_tick_time - (time.time() - tick_start)
            print('sleeping for', sleep_time)
            if sleep_time > 0.0:
                time.sleep(sleep_time)
