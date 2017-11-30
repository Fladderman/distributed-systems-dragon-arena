#!/usr/local/bin/python2

# server
import sys
import os
import time
import json
import threading


# Add parent directory to the syspath
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
sys.path.insert(1, os.path.join(sys.path[0], '../drawing'))
from DragonArenaNew import DragonArena
from drawing import BoardVisualization
from socket_communications import ServerSocket

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
    def __init__(self, server_socket, client_fd, game, drawing):
        """

        :param server_socket: Instance of class ServerSocket
        :param client_fd: socket file descriptor
        :param game: Instance of DragonArena
        :param drawing: For visualization
        """
        threading.Thread.__init__(self)
        self.client_fd = client_fd
        self.server_socket = server_socket
        self.ip, self.port = client_fd.getpeername()
        self.game = game
        self.drawing = drawing

    def run(self):
        """
        Handle connection to client
        :return:
        """
        self.server_socket.send_data("ACK", sock_fd=self.client_fd)
        self.game.spawn_knight()  # Always use world 0 when server/client based

        while True:
            #  TODO Add more stuff here, such as client requesting move, attack, disconnect etc

            time.sleep(3)

            # Draw board
            self.drawing.draw_game()
        pass


class Server:
    """
    Handle all incoming client connections
    """

    def __init__(self):
        """
        Initialize all server specific values
        """

        # Create socket object
        self.server_socket = ServerSocket()

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

        client_socket = self.server_socket.accept()
        self._add_client(client_socket)

    def _add_client(self, client_socket):
        t = ClientHandler(self.server_socket, client_socket, self.game, self.drawing)
        t.daemon = True
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
