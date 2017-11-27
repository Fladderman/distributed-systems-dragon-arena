import threading, time, json, socket
import messaging, das_game_settings

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


MASTER_SERVER = 0
class Server:

    '''
    Server will first attempt to connect to other servers
    '''
    def __init__(self):
        '''Prep phase. gotta handshake with everyone first'''
        self._accepting_clients = False;
        self._clients = dict() # maps addr to sock
        self._other_server_socks = [None for _ in range(0, len(das_game_settings.server_addresses))]
        self._handshake_with_others()
        i_am_first = all(None==item for item in self._other_server_socks)
        self._game_state = Server.create_fresh_state() if i_am_first else self._get_state_from_someone()

        my_index = self._join_server_system()
        print('socks:', self._other_server_socks)
        print('done')
        time.sleep(3.0)
        my_port = das_game_settings.server_addresses[my_index][1]
        print('my_port', my_port)

        self._my_server_id = None
        self._accepting_thread = threading.Thread(
            target=Server.handle_incoming_clients,
            args=(self, my_port),
        )
        self._accepting_thread.daemon = True
        self._accepting_thread.start()
        self._requests = []
        self._req_lock = threading.Lock()
        print('setup done')

    def _get_state_from_someone(self):
        # TODO contact another server with `self._other_server_socks`
        # return the game state given by someone there
        return "LELELE IDK ROFLMAO"

    @staticmethod
    def create_fresh_state():
        # TODO create a fresh game state object and return
        return "LELELELE GAME STATE"

    def _handshake_with_others(self):
        '''
        first try to connect to all, populating self._other_server_socks
        determine my ID
        then send each a M_SERV_HELLO
        return my ID
        '''
        for index, addr in enumerate(das_game_settings.server_addresses):
            socket.setdefaulttimeout(2.0)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((ip, port))
                self._other_server_socks = sock
                print('successfully conencted to', index, 'at', addr)
            except:
                print('failed to connect to ', index, 'at', addr)
        my_index = (i for i,v in enumerate(self._other_server_socks) if v==None).next()
        assert my_index is not None
        msg = messaging.M_SERV_HELLO
        for index, addr in enumerate(das_game_settings.server_addresses):
            if self._other_server_socks[index] != None:
                print('writing', msg, 'to', index, addr)
                messaging.write_msg_to(self._other_server_socks[index], msg)
            else:
                print('failed to write to', index, addr)
        return my_index



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
                print('tick drained', my_req_pool)
                for msg in my_req_pool:
                    c_sock = self._clients[msg.sender]
                    response = messaging.M_SERV_WELCOME(_my_server_id)
                    messaging.write_msg_to(c_sock, response, packer=maini_loop_packer)
                    print('popping')
                    self._clients.pop(msg.sender)



            '''SLEEP STEP'''
            sleep_time = das_game_settings.server_min_tick_time - (time.time() - tick_start)
            if sleep_time > 0.0:
                time.sleep(sleep_time)
