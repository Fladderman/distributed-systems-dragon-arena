import threading, time, json, socket
import messaging, das_game_settings
import state_dummy

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
    '''
    Server will first attempt to connect to other servers
    '''
    def __init__(self, server_id): #server_id == index
        '''Prep phase. gotta handshake with everyone first'''
        self._server_id = server_id
        self._accepting_clients = False;
        self._serv_sockets = self._connect_to_other_servers()
        print('_serv_sockets:', self._serv_sockets)

        id_of_authority_server = next( (x for x in self._serv_sockets if x!=None), None)
        print('id_of_authority_server:', id_of_authority_server)
        self._game_state = Server.create_fresh_state()\
            if id_of_authority_server==None\
            else self._get_state_from_someone(self._serv_sockets[id_of_authority_server])

        self._clients = dict() #addr --> socket
        self._requests = []
        self._req_lock = threading.Lock()

        print('done')
        time.sleep(3.0)
        my_port = das_game_settings.server_addresses[self._server_id][1]
        print('my_port', my_port)
        self._accepting_thread = threading.Thread(
            target=Server.handle_incoming_clients,
            args=(self, my_port),
        )
        self._accepting_thread.daemon = True
        self._accepting_thread.start()
        self._accepting_clients = True;
        print('setup done')

    def _get_state_from_someone(self, authority_server_socket):
        messaging.write_msg_to(authority_server_socket, messaging.M_SERV_SYNC_REQ)
        msg_check = lambda m:\
            isinstance(m, Message)\
            and m.msg_header == messaging.header2int['SERV_SYNC_REPLY']
        reply = messaging.read_first_message_matching(authority_server_socket, msg_check)
        return reply.args[0]

    def _get_state_from_someone(self):
        # TODO contact another server with `self._other_server_socks`
        # return the game state given by someone there
        return state_dummy.StateDummy()

    @staticmethod
    def create_fresh_state():
        # TODO create a fresh game state object and return
        return state_dummy.StateDummy()

    def _connect_to_other_servers(self):
        '''
        first try to connect to all, populating self._other_server_socks
        then send each a M_SERV_HELLO
        '''
        serv_sockets = [None for _ in range(0, len(das_game_settings.server_addresses))]
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



    def handle_client_incoming(self, client_sock, client_addr):
        for msg in messaging.read_many_msgs_from(client_sock):
            print('loop')
            if msg != None:
                # todo handle ping messages?
                self._requests.append(msg)
                print('msg yielded', msg)
                msg.sender = client_addr #todo make this some kind of client id
                with self._req_lock:
                    self._requests.append(msg)
            else:
                if client_addr not in self._clients:
                    print('sock dead. killing incoming reader daemon')
                    return

    def handle_incoming_clients(self, port):
        server_acceptor = ServerAcceptor(port)
        while True:
            # print('acc loop')
            if self._accepting_clients:
                new_socket, new_addr = server_acceptor.next_incoming()
                # print('new_client_tuple', (new_addr, new_socket))
                if new_socket != None:
                    with self._req_lock:
                        self._clients[new_addr] = new_socket
                    client_incoming_thread = threading.Thread(
                        target=Server.handle_client_incoming,
                        args=(self, new_socket, new_addr),
                    )
                    client_incoming_thread.daemon = True
                    client_incoming_thread.start()
            else:
                time.sleep(1)
        return 5

    def main_loop(self):
        while True:
            tick_start = time.time()

            '''SWAP BUFFERS'''
            with self._req_lock:
                my_req_pool = self._requests
                self._requests = []
            if my_req_pool:
                # DEBUG. nothing in this control branch is realistic. just for testing
                print('tick drained', my_req_pool)
                for msg in my_req_pool:
                    if msg.sender in self._clients:
                        c_sock = self._clients[msg.sender]
                        response = messaging.M_S2C_WELCOME(self._server_id)
                        print('response', response)
                        messaging.write_msg_to(c_sock, response)
                        print('popping')
                        self._clients.pop(msg.sender)



            '''SLEEP STEP'''
            sleep_time = das_game_settings.server_min_tick_time - (time.time() - tick_start)
            if sleep_time > 0.0:
                time.sleep(sleep_time)
