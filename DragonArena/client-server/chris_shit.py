import threading
import socket
import msgpack
import time
socket.setdefaulttimeout(1) #DEBUG

class Message:
    def __init__(self, data):
        self.data = data

    def write_to(self, socket):
        naked_msg = self.data
        msgpack.pack(naked_msg, socket)

    def read_from(socket):
        naked_msg = msgpack.unpack(socket)
        print ("msgpack unpacked", naked_msg)
        return Message(naked_msg)

'''returns a connected client-side socket'''
def sock_client(ip, port):
    assert type(ip) is str and type(port) is int
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    return s

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
            return (client_socket, addr)
        except:
            return None

class Server:
    def __init__(self, port):
        self._accepting_new_clients = True;
        self._accepting_clients = True
        self._clients = []
        self._accepting_thread = threading.Thread(
            target=Server.handle_incoming_clients,
            args=(self, port),
        )
        self._accepting_thread.setDaemon = True
        self._accepting_thread.start()

    def handle_incoming_clients(self, port):
        server_acceptor = ServerAcceptor(port)
        while True:
            print('acc loop')
            if self._accepting_clients:
                x = server_acceptor.next_incoming()
                print('x', x)
                if x != None:
                    self._clients.append(x[0])
            else:
                time.sleep(1)
        return 5


    def main_loop(self):
        while True:
            print("server tick!. have ", self._clients, "clients")
            time.sleep(1)
