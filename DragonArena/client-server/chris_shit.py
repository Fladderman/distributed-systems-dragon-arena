import threading, socket, msgpack, time
socket.setdefaulttimeout(2) #DEBUG
from StringIO import StringIO
#from pprint import pprint

TICK_MIN_TIME = 1.0

class Message:
    def __init__(self, msg_header, sender, args):
        assert isinstance(msg_header, int)
        assert isinstance(sender, int)
        assert isinstance(args, list)
        self.msg_header = msg_header
        self.sender = sender
        self.args = args

    def serialize(self):
        return (self.msg_header, self.sender, self.args)

    @staticmethod
    def deserialize(serialized_msg):
        msg_header = serialized_msg[0]
        sender = serialized_msg[1]
        args = serialized_msg[2]
        assert isinstance(msg_header, int)
        assert isinstance(sender, int)
        assert isinstance(args, list)
        return Message(msg_header, sender, args)

    def __repr__(self):
        return (
            'Message::' + str(self.msg_header) + ' from '
            + str(self.sender) + ' with args:' + str(self.args)
        )


def read_all_from(socket):
    '''
    Generator object. will read from socket
    blocks until it yields a Message or None
        yields *something* regularly to allow early termination ;)
    returns when socket is dead.
    '''
    unpacker = msgpack.Unpacker()
    while True:
        try:
            x = socket.recv(256)
            print('x', x)
            if x == '':
                print('socket dead!')
                return
                #connection closed!
            unpacker.feed(x)
            for package in unpacker:
                msg = Message.deserialize(package)
                yield msg
        except:
            yield None


def write_to(socket, msg):
    assert isinstance(msg, Message)
    '''
    send the given msg into the socket
    '''
    myfile = StringIO()
    packer = msgpack.Packer()
    myfile.write(packer.pack(msg.serialize()))
    myfile = StringIO(myfile.getvalue())
    #pprint(vars(myfile))
    tot_bytes = len(myfile.buf)
    sent_now = 1
    while sent_now != 0:
        sent_now = socket.send(myfile.read(tot_bytes))
    print('done')

class ServerAcceptor:
    def __init__(self, port):
        assert type(port) is int and port > 0
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", port))
        BACKLOG = 5
        self._sock.listen(BACKLOG)

    def next_incoming(self):
        try:
            client_socket, addr = self._sock.accept()
            return client_socket, addr
        except:
            return None, None

class Server:
    def __init__(self, server_id, port):
        self._server_id = server_id
        self._accepting_new_clients = True;
        self._accepting_clients = True
        self._clients = dict() # maps addr to sock
        self._accepting_thread = threading.Thread(
            target=Server.handle_incoming_clients,
            args=(self, port),
        )
        self._accepting_thread.daemon = True
        self._accepting_thread.start()
        self._requests = []
        self._req_lock = threading.Lock()

    def handle_client_incoming(self, client_sock, client_addr):
        for msg in read_all_from(client_sock):
            print('msg yielded', msg)
            if msg != None:
                with self._req_lock:
                    self._requests.append(msg)

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

            '''SLEEP STEP'''
            sleep_time = TICK_MIN_TIME - (time.time() - tick_start)
            if sleep_time > 0.0:
                time.sleep(sleep_time)

class Client:
    def __init__(self):
        

    '''
    attempts to connect
    '''
    @staticmethod
    def sock_client(ip, port, timeout=2):
        assert isinstance(ip, str)
        assert isinstance(port, int)
        assert isinstance(timeout, int)
        try:
            socket.setdefaulttimeout(timeout)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            return
        except:
            return None
