#!/usr/local/bin/python2

# server
import socket
import sys
import os
import json
import threading

# Add parent directory to the syspath
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
sys.path.insert(1, os.path.join(sys.path[0], '../drawing'))
from DragonArenaNew import DragonArena
from drawing import BoardVisualization

# Import settings from settings file
settings = json.load(open('../settings.json'))
BACKLOG = settings["server"]["backlog"]
MAX_CLIENTS = settings["game"]["max_players"]
PORTS = settings["server"]["ports"]


# Random values for amount of worlds, dragons etc to create
# --------------------------------------
no_of_dragons = 1
no_of_knights = 10
no_of_worlds = 1
# --------------------------------------


class ClientHandler(threading.Thread):
    """
    Handle client connection to server
    """
    def __init__(self, fd, game, world):
        threading.Thread.__init__(self)
        self.fd = fd #?? fd is the socket
        self.ip, self.port = fd.getpeername()
        self.game = game
        self.world = world

    def run(self):
        """
        Handle connection to client
        :return:
        """
        self.fd.send("ACK")
        self.game.place_knight(self.world)  # Always use world 0 when server/client based

        # TODO Add more stuff here, such as client requesting move, attack, disconnect etc

        pass


class Server:
    """
    Handle all incoming client connections
    """

    def __init__(self):
        """
        Initialize all server specific values
        """

        self.connected_clients = []

        # Opens socket for server
        self.server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)

        # TODO Register server on some kind of register, which keeps a
        # TODO track of all servers.

        if self._bord_exists():
            # TODO Copy board to store locally on this server
            self.game = None
            pass
        else:
            # TODO Create bord
            self.game = self._create_bord()

            # Spawn randomly many knights here if there are no clients actually connecting
            # self.game.spawn_random_knights(no_of_knights)

        self.drawing = BoardVisualization(self.game)
        self.drawing.draw_game()
        self.start()

    def start(self):
        """
        Start server. Accepts client requests and
        adds them to the connected client list.
        :return:
        """
        host = socket.gethostname()
        for port in PORTS:
            try:
                self.server_socket.bind((host, port))
            except socket.error:
                # print "oh shit"
                continue

        # Queue max 5 requests
        self.server_socket.listen(BACKLOG)

        # spawn draw thread idgaf

        while True:
            # Establish a connection
            client_socket, addr = self.server_socket.accept()

            if len(self.connected_clients) < MAX_CLIENTS:
                self._add_client(client_socket, addr)
            else:
                client_socket.send("NACK")
                self._print("Declined a connection from %s" % str(addr))
            client_socket.close()

    def _add_client(self, client_socket, addr):
        t = ClientHandler(client_socket, self.game, self.game.worlds[0])
        self.connected_clients.append(t)
        t.start()

    def _bord_exists(self):
        # TODO Check if bord already exists, e.g. send request asking
        # TODO to all other servers in the list of servers in the settings file

        return False  # Change to value

    def _create_bord(self):
        """
        Create a new bord containing dragons
        :return:
        """
        # TODO synchronize so that only one server does this at a time!!

        return DragonArena(no_of_dragons, settings["game"]["width"], settings["game"]["height"])

    @staticmethod
    def _print(value):
        print "{}".format(value)
        sys.stdout.flush()


if __name__ == "__main__":
    server = Server()

    server.start()
