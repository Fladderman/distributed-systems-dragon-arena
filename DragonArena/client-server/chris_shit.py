import threading
import socket
import msgpack
import time
socket.setdefaulttimeout(2) #DEBUG
from StringIO import StringIO
from pprint import pprint

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
        return str('Message::' + str(self.msg_header) +
        " from " + str(self.sender) + ' with args:', self.args)


'''returns a connected client-side socket'''
def sock_client(ip, port):
    assert type(ip) is str and type(port) is int
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    return s


def write_to(socket, msg):
    assert isinstance(msg, Message)
    myfile = StringIO()
    serialized_msg = msg.serialize()
    packer = msgpack.Packer()
    myfile.write(packer.pack(serialized_msg))
    myfile = StringIO(myfile.getvalue())
    pprint(vars(myfile))
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
    def __init__(self, port):
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
        print('yeee:::', self, client_sock, client_addr)
        unpacker = msgpack.Unpacker()
        while client_addr in self._clients:
            unpacker.feed(client_sock.recv(1))
            for package in unpacker:
                print('package: ', package)
                msg = Message.deserialize(package)
                print('good message', str(msg))

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
            # with self._req_lock:
            #     print("server tick!. have ", self._clients, "clients")
            time.sleep(1)
