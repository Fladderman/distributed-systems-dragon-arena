#!/usr/local/bin/python2

# server
import socket
import sys
import json

# Import settings from settings file
settings = json.load(open('settings.json'))
BACKLOG = settings["server"]["backlog"]
MAX_CLIENTS = settings["game"]["max_players"]
PORTS = settings["server"]["ports"]


class Server:
    def __init__(self):
        self.connected_clients = set()

        # Opens socket for server
        self.server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)

        # TODO Register server on some kind of register, which keeps a
        # TODO track of all servers.

    def start(self):
        host = socket.gethostname()
        self.server_socket.bind((host, PORTS[0]))

        # Queue max 5 requests
        self.server_socket.listen(BACKLOG)

        while True:
            # Establish a connection
            client_socket, addr = self.server_socket.accept()

            if len(self.connected_clients) < MAX_CLIENTS:
                self.connected_clients.add(addr)
                client_socket.send("ACK")
                self._print("Accepted a connection from %s" % str(addr))
            else:
                client_socket.send("NACK")
                self._print("Declined a connection from %s" % str(addr))
            client_socket.close()

    @staticmethod
    def _print(value):
        print "{}".format(value)
        sys.stdout.flush()


if __name__ == "__main__":
    server = Server()

    server.start()
