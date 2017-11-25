import socket
import json

import sys

settings = json.load(open('../settings.json'))
MSGLEN = settings['communication']['max_len']
BACKLOG = settings["server"]["backlog"]
MAX_CLIENTS = settings["game"]["max_players"]
PORTS = settings["server"]["ports"]

"""
Copied from python2 tutorial, needs improvement!
"""


class SocketHandling:
    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def send_data(self, msg, msg_len=MSGLEN, sock_fd=None):
        sock_fd.send(msg)
        return
        # TODO for some reason the code below here is not working ?!

        if sock_fd is None:
            sock_fd = self.sock
        total_sent = 0
        while total_sent < msg_len:
            sent = sock_fd.send(msg[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent = total_sent + sent

    def receive_data(self, msg_len=MSGLEN):
        chunks = []
        bytes_recd = 0
        while bytes_recd < msg_len:
            chunk = self.sock.recv(min(msg_len - bytes_recd, 2048))
            if chunk == '':
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return ''.join(chunks)


class ServerSocket(SocketHandling):
    def __init__(self, sock=None):
        SocketHandling.__init__(self, sock=sock)

        self.connected_clients = []

        host = socket.gethostname()
        for port in PORTS:
            try:
                self.sock.bind((host, port))
            except socket.error:
                # print "oh shit"
                continue

        # Queue max BACKLOG requests
        self.sock.listen(BACKLOG)

    def accept(self):
        """
        Accept an incoming client
        :return: client_sock - client_socket upon success
                 None - upon failure
        """
        while True:
            # Establish a connection
            client_socket, addr = self.sock.accept()

            if len(self.connected_clients) < MAX_CLIENTS:
                self.connected_clients.append((client_socket, addr))

                return client_socket
            else:
                client_socket.send("NACK")

                return None

    def close_clients(self):
        for x in self.connected_clients:
            x[0].close()


class ClientSocket(SocketHandling):
    def __init__(self, sock=None):
        SocketHandling.__init__(self, sock=sock)

    def connect(self, host, port):
        self.sock.connect((host, port))

    def close(self):
        self.sock.close()
